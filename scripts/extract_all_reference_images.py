"""
scripts/extract_all_reference_images.py

Unified Image Extractor for All Authoritative Pathology Reference Documents:
- Robbins & Cotran Pathologic Basis of Disease 11th Edition
- Robbins and Cotran Review of Pathology 4th Edition
- Sternberg's Diagnostic Surgical Pathology Review 2nd Edition

Extracts raw figure plates, microscopy photos, diagrams, and gross specimen images
as PNG files under data/processed/images/ with structured provenance in filename.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf  # PyMuPDF

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("extract_images")

RAW_DOCS_DIR = PROJECT_ROOT / "data" / "raw" / "reference_documents"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "images"

BOOK_CONFIGS = {
    "robbins_pathologic_basis_11th": {
        "glob_pattern": "*Pathologic_Basis*11th*.pdf",
        "file_prefix": "img-robins",
        "source_name": "Robbins & Cotran Pathologic Basis of Disease",
        "page_offset": 16,
    },
    "robbins_review": {
        "glob_pattern": "*Review_of_Pathology*.pdf",
        "fallback_pattern": "*Review of Pathology*.pdf",
        "file_prefix": "img-robreview",
        "source_name": "Robbins and Cotran Review of Pathology",
        "page_offset": 5,
    },
    "sternberg_review_2nd": {
        "glob_pattern": "*Sternberg*.pdf",
        "file_prefix": "img-sternberg",
        "source_name": "Sternberg's Diagnostic Surgical Pathology Review",
        "page_offset": 14,
    },
}


def find_book_pdf(config: Dict[str, Any]) -> Optional[Path]:
    """Finds the book PDF based on glob patterns."""
    candidates = list(RAW_DOCS_DIR.glob(config["glob_pattern"]))
    if not candidates and "fallback_pattern" in config:
        candidates = list(RAW_DOCS_DIR.glob(config["fallback_pattern"]))
    return candidates[0] if candidates else None


def extract_images_from_book(
    book_key: str,
    output_dir: Path = OUTPUT_DIR,
    max_pages: Optional[int] = None,
    start_page: int = 1,
) -> int:
    """Extracts all embedded images from a book PDF."""
    config = BOOK_CONFIGS[book_key]
    pdf_path = find_book_pdf(config)
    if not pdf_path or not pdf_path.is_file():
        logger.error(f"PDF for {book_key} not found in {RAW_DOCS_DIR}")
        return 0

    logger.info(f"📖 Opening PDF: {pdf_path.name}")
    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)
    logger.info(f"   Document contains {total_pages:,} pages.")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = config["file_prefix"]
    extracted_count = 0
    skipped_existing = 0

    end_page = min(total_pages, start_page + max_pages - 1) if max_pages else total_pages

    for page_idx in range(start_page - 1, end_page):
        page_num = page_idx + 1
        page = doc.load_page(page_idx)
        img_list = page.get_images(full=True)
        if not img_list:
            continue

        for img_idx, img in enumerate(img_list, start=1):
            xref = img[0]
            img_name = f"{prefix}-p{page_num:04d}-f{img_idx:03d}.png"
            img_path = output_dir / img_name

            if img_path.exists():
                skipped_existing += 1
                continue

            try:
                pix = pymupdf.Pixmap(doc, xref)
                # If pixmap has colorspace not supported directly by PNG (e.g. CMYK), convert to RGB
                if pix.colorspace not in (pymupdf.csGRAY, pymupdf.csRGB) or pix.n >= 5:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                img_bytes = pix.tobytes("png")
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                extracted_count += 1
            except Exception as e:
                logger.warning(f"Failed to extract image {img_idx} on page {page_num}: {e}")

    logger.info(
        f"✅ {book_key}: Extracted {extracted_count:,} new images "
        f"({skipped_existing:,} already existed) to {output_dir}"
    )
    return extracted_count


def main():
    parser = argparse.ArgumentParser(description="Extract images from reference documents")
    parser.add_argument(
        "--book",
        choices=list(BOOK_CONFIGS.keys()) + ["all-missing"],
        default="all-missing",
        help="Which book to extract (default: all-missing)",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Destination directory")
    parser.add_argument("--max-pages", type=int, help="Limit number of pages")
    parser.add_argument("--start-page", type=int, default=1, help="Start page")
    args = parser.parse_args()

    target_books = (
        ["robbins_review", "sternberg_review_2nd"]
        if args.book == "all-missing"
        else [args.book]
    )

    total_extracted = 0
    for book in target_books:
        logger.info(f"🚀 Starting extraction for {book}...")
        count = extract_images_from_book(
            book_key=book,
            output_dir=args.output_dir,
            max_pages=args.max_pages,
            start_page=args.start_page,
        )
        total_extracted += count

    logger.info(f"🎉 All extraction tasks complete! Total new images extracted: {total_extracted:,}")


if __name__ == "__main__":
    main()
