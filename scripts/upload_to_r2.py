"""
scripts/upload_to_r2.py

High-Performance Concurrent Cloudflare R2 Uploader for Curated Pathology Images.
Uploads verified histology, gross pathology, and diagram assets to the
Cloudflare R2 'docedge' bucket via S3v4 API and registers CDN URLs in Neon PostgreSQL.

Usage:
  # Test connection and bucket access:
  python scripts/upload_to_r2.py --test-connection

  # Upload all 2,165 curated valid images using 12 concurrent workers:
  python scripts/upload_to_r2.py --concurrency 12
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("r2_uploader")

VALID_MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "images" / "valid_images_manifest.json"
CURATED_DIR = PROJECT_ROOT / "data" / "processed" / "images" / "curated_valid"
RECEIPT_PATH = PROJECT_ROOT / "data" / "processed" / "images" / "r2_uploaded_manifest.json"


def resolve_source_short_name(filename: str) -> str:
    """Derives source short name from filename prefix."""
    if filename.startswith("img-robins"):
        return "robbins_pathologic_basis_11th"
    elif filename.startswith("img-robreview"):
        return "robbins_review"
    elif filename.startswith("img-sternberg"):
        return "sternberg_review_2nd"
    return "general"


def get_r2_client(
    account_id: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
):
    """Initializes and returns an S3 client configured for Cloudflare R2."""
    account_id = account_id or os.getenv("R2_ACCOUNT_ID") or os.getenv("CLOUDFLARE_ACCOUNT_ID")
    access_key = access_key_id or os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")

    if not account_id or not access_key or not secret_key:
        logger.error(
            "Missing Cloudflare R2 credentials. Please set in .env:\n"
            "  R2_ACCOUNT_ID=<your-cloudflare-account-id>\n"
            "  R2_ACCESS_KEY_ID=<your-r2-api-access-key>\n"
            "  R2_SECRET_ACCESS_KEY=<your-r2-api-secret-key>\n"
            "  R2_BUCKET_NAME=docedge\n"
            "  R2_PUBLIC_URL=https://<your-public-r2-domain-if-any>"
        )
        return None

    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4", max_pool_connections=25),
        region_name="auto",
    )


def test_connection(s3_client, bucket_name: str) -> bool:
    """Verifies that R2 bucket exists and is accessible."""
    logger.info(f"🔍 Testing access to R2 bucket '{bucket_name}'...")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"✅ Successfully connected to R2 bucket '{bucket_name}'!")
        return True
    except ClientError as e:
        err_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"❌ Could not access bucket '{bucket_name}': {err_code} ({e})")
        return False


def upload_single_image(
    s3_client,
    img: Dict[str, Any],
    bucket_name: str,
    public_url_base: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Uploads an individual image to R2."""
    filename = img["filename"]
    local_path = CURATED_DIR / filename
    if not local_path.exists():
        local_path = PROJECT_ROOT / "data" / "processed" / "images" / filename

    if not local_path.exists():
        logger.warning(f"File not found on disk: {filename}")
        return None

    source = img.get("source_short_name") or resolve_source_short_name(filename)
    key = f"pathology/{source}/{filename}"

    s3_client.upload_file(
        Filename=str(local_path),
        Bucket=bucket_name,
        Key=key,
        ExtraArgs={
            "ContentType": "image/png",
            "Metadata": {
                "sha256": img.get("sha256", ""),
                "pdf_page": str(img.get("pdf_page", "")),
                "triage_class": img.get("triage_class", ""),
            },
        },
    )

    if public_url_base:
        cdn_url = f"{public_url_base.rstrip('/')}/{key}"
    else:
        cdn_url = f"https://{bucket_name}.r2.cloudflarestorage.com/{key}"

    return {
        "extraction_id": img.get("extraction_id"),
        "filename": filename,
        "r2_key": key,
        "r2_bucket": bucket_name,
        "cdn_url": cdn_url,
        "sha256": img.get("sha256"),
        "width": img.get("width"),
        "height": img.get("height"),
        "pdf_page": img.get("pdf_page"),
        "textbook_page": img.get("textbook_page"),
        "triage_class": img.get("triage_class"),
    }


def upload_images(
    s3_client,
    bucket_name: str,
    public_url_base: Optional[str] = None,
    max_uploads: Optional[int] = None,
    concurrency: int = 10,
) -> Dict[str, Any]:
    """Uploads curated valid images to Cloudflare R2 bucket with concurrency."""
    if not VALID_MANIFEST_PATH.exists():
        logger.error(f"Valid images manifest not found: {VALID_MANIFEST_PATH}")
        return {}

    with open(VALID_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    images = manifest_data.get("images", [])
    if max_uploads:
        images = images[:max_uploads]

    total_count = len(images)
    logger.info(f"🚀 Starting concurrent upload of {total_count:,} images to R2 '{bucket_name}' ({concurrency} workers)...")

    # Load existing receipts to support resuming
    existing_receipts: Dict[str, Any] = {}
    if RECEIPT_PATH.exists():
        try:
            with open(RECEIPT_PATH, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                existing_receipts = {
                    item["filename"]: item for item in old_data.get("uploaded_images", [])
                }
        except Exception:
            pass

    to_upload = [img for img in images if img["filename"] not in existing_receipts]
    skipped_count = total_count - len(to_upload)
    uploaded_records: List[Dict[str, Any]] = list(existing_receipts.values())

    logger.info(f"   {skipped_count:,} images already uploaded (skipping). {len(to_upload):,} remaining to upload.")

    success_count = 0
    failed_count = 0
    lock = threading.Lock()
    progress_counter = skipped_count

    def _worker(img_item):
        nonlocal success_count, failed_count, progress_counter
        try:
            record = upload_single_image(
                s3_client=s3_client,
                img=img_item,
                bucket_name=bucket_name,
                public_url_base=public_url_base,
            )
            if record:
                with lock:
                    uploaded_records.append(record)
                    success_count += 1
                    progress_counter += 1
                    if progress_counter % 50 == 0 or progress_counter == total_count:
                        logger.info(f"   [{progress_counter}/{total_count}] Uploaded {record['filename']} -> {record['r2_key']}")
            else:
                with lock:
                    failed_count += 1
        except Exception as e:
            with lock:
                failed_count += 1
            logger.error(f"Failed to upload {img_item.get('filename')}: {e}")

    if to_upload:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            executor.map(_worker, to_upload)

    summary = {
        "bucket_name": bucket_name,
        "total_targets": total_count,
        "uploaded_new": success_count,
        "skipped_existing": skipped_count,
        "failed": failed_count,
        "uploaded_images": uploaded_records,
    }

    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\n=======================================================")
    logger.info(f"🎉 R2 Upload Complete! Uploaded: {success_count:,} | Skipped: {skipped_count:,} | Failed: {failed_count:,}")
    logger.info(f"📄 Upload manifest saved to {RECEIPT_PATH}")

    # Synchronize storage URIs to PostgreSQL database
    try:
        sync_storage_uris_to_db(uploaded_records)
    except Exception as e:
        logger.warning(f"Could not sync storage URIs to database: {e}")

    return summary


def sync_storage_uris_to_db(uploaded_records: List[Dict[str, Any]]) -> int:
    """Updates storage_uri for ImageAssets in PostgreSQL/Neon."""
    if not uploaded_records:
        return 0
    from database.db import get_engine, get_session_factory
    from database.models import ImageAsset

    engine = get_engine()
    session_factory = get_session_factory(engine)
    logger.info(f"🔄 Syncing {len(uploaded_records):,} CDN URLs to Neon database...")
    updated = 0
    with session_factory() as db:
        # Group by sha for rapid bulk update
        for idx, r in enumerate(uploaded_records, start=1):
            sha = r.get("sha256")
            cdn_url = r.get("cdn_url")
            if sha and cdn_url:
                asset = db.query(ImageAsset).filter(ImageAsset.sha256 == sha).first()
                if asset and asset.storage_uri != cdn_url:
                    asset.storage_uri = cdn_url
                    updated += 1
            if idx % 200 == 0:
                db.commit()
        db.commit()
    logger.info(f"✅ Synced {updated:,} storage_uri values to Neon database.")
    return updated


def main():
    parser = argparse.ArgumentParser(description="Upload pathology images to Cloudflare R2 bucket docedge")
    parser.add_argument("--bucket", default=os.getenv("R2_BUCKET_NAME", "docedge"), help="R2 bucket name (default: docedge)")
    parser.add_argument("--test-connection", action="store_true", help="Test R2 credentials and bucket existence")
    parser.add_argument("--max-uploads", type=int, help="Limit number of images to upload")
    parser.add_argument("--concurrency", type=int, default=12, help="Number of concurrent upload workers")
    parser.add_argument("--public-url", default=os.getenv("R2_PUBLIC_URL"), help="Public CDN URL prefix")
    args = parser.parse_args()

    s3_client = get_r2_client()
    if not s3_client:
        sys.exit(1)

    if args.test_connection:
        ok = test_connection(s3_client, args.bucket)
        sys.exit(0 if ok else 1)

    upload_images(
        s3_client=s3_client,
        bucket_name=args.bucket,
        public_url_base=args.public_url,
        max_uploads=args.max_uploads,
        concurrency=args.concurrency,
    )


if __name__ == "__main__":
    main()
