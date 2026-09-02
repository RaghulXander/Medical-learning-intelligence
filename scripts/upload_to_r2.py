"""
scripts/upload_to_r2.py

Cloudflare R2 Uploader for Curated Pathology Images.
Uploads verified histology, gross pathology, and diagram assets to the
Cloudflare R2 'docedge' bucket via the S3-compatible API.

Usage:
  # Test connection and bucket access:
  python scripts/upload_to_r2.py --test-connection

  # Upload a test batch of 10 images:
  python scripts/upload_to_r2.py --max-uploads 10

  # Upload all 2,165 curated valid images:
  python scripts/upload_to_r2.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
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
        config=Config(signature_version="s3v4"),
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


def upload_images(
    s3_client,
    bucket_name: str,
    public_url_base: Optional[str] = None,
    max_uploads: Optional[int] = None,
) -> Dict[str, Any]:
    """Uploads curated valid images to Cloudflare R2 bucket."""
    if not VALID_MANIFEST_PATH.exists():
        logger.error(f"Valid images manifest not found: {VALID_MANIFEST_PATH}")
        logger.error("Run 'python scripts/curate_reference_images.py export-valid' first.")
        return {}

    with open(VALID_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    images = manifest_data.get("images", [])
    if max_uploads:
        images = images[:max_uploads]

    logger.info(f"🚀 Preparing to upload {len(images):,} images to R2 bucket '{bucket_name}'...")

    uploaded_records = []
    success_count = 0
    skipped_count = 0
    failed_count = 0

    # Load existing receipts to support resuming
    existing_receipts = {}
    if RECEIPT_PATH.exists():
        try:
            with open(RECEIPT_PATH, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                existing_receipts = {item["filename"]: item for item in old_data.get("uploaded_images", [])}
        except Exception:
            pass

    for idx, img in enumerate(images, start=1):
        filename = img["filename"]
        local_path = CURATED_DIR / filename
        if not local_path.exists():
            local_path = PROJECT_ROOT / "data" / "processed" / "images" / filename

        if not local_path.exists():
            logger.warning(f"File not found on disk: {filename}")
            failed_count += 1
            continue

        # Check if already uploaded
        if filename in existing_receipts:
            uploaded_records.append(existing_receipts[filename])
            skipped_count += 1
            continue

        # S3 object key: pathology/{source_short_name}/{filename}
        source = img.get("source_short_name", "general")
        key = f"pathology/{source}/{filename}"

        try:
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

            # Build URL
            if public_url_base:
                cdn_url = f"{public_url_base.rstrip('/')}/{key}"
            else:
                cdn_url = f"https://{bucket_name}.r2.cloudflarestorage.com/{key}"

            record = {
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
            uploaded_records.append(record)
            success_count += 1

            if idx % 25 == 0 or idx == len(images):
                logger.info(f"   [{idx}/{len(images)}] Uploaded {filename} -> {key}")

        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            failed_count += 1

    summary = {
        "bucket_name": bucket_name,
        "total_targets": len(images),
        "uploaded_new": success_count,
        "skipped_existing": skipped_count,
        "failed": failed_count,
        "uploaded_images": uploaded_records,
    }

    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"🎉 Upload batch complete! Uploaded: {success_count:,} | Skipped: {skipped_count:,} | Failed: {failed_count:,}")
    logger.info(f"📄 Upload manifest saved to {RECEIPT_PATH}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Upload pathology images to Cloudflare R2 bucket docedge")
    parser.add_argument("--bucket", default=os.getenv("R2_BUCKET_NAME", "docedge"), help="R2 bucket name (default: docedge)")
    parser.add_argument("--test-connection", action="store_true", help="Test R2 credentials and bucket existence")
    parser.add_argument("--max-uploads", type=int, help="Limit number of images to upload")
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
    )


if __name__ == "__main__":
    main()
