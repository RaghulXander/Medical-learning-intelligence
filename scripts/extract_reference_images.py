#!/usr/bin/env python
"""
Extract all figures / plates from the Robbins & Cotran Pathologic Basis of Disease (11th ed.) PDF.

Outputs:
  - PNG files under data/processed/images/
  - manifest.json with provenance metadata.
  - logs/extract_images.log (captures per‑page progress and any warnings).

Configuration is derived from the user request:
  * PDF path: data/raw/reference_documents/Robbins_and_Cotran_Pathologic_Basis_of_Disease_11th_Edition.pdf
  * DPI: 300 (original image resolution is retained; DPI is noted in the manifest)
  * Single‑threaded execution (simpler, deterministic logs)
  * Log file written to logs/extract_images.log for easy traceability.
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Dict

import fitz  # PyMuPDF – make sure the dependency exists in the venv

# ----------------------------------------------------------------------
# Configuration – adjust if needed
# ----------------------------------------------------------------------
PDF_PATH = Path("data/raw/reference_documents/Robbins_and_Cotran_Pathologic_Basis_of_Disease_11th_Edition.pdf")
OUTPUT_DIR = Path("data/processed/images")
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "extract_images.log"
DPI = 300  # Desired image resolution (metadata only; we keep original pixel data)

# Ensure output and log directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Set up logging – both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("robins_extractor")


def _extract_caption(page: fitz.Page, img_rect: fitz.Rect) -> str:
    """Grab the textual block immediately below an image rectangle.
    Heuristic: look for the nearest text block within 50 pt vertical distance that contains
    the word "Fig" or "Figure". Returns an empty string if none found.
    """
    blocks = page.get_text("blocks")
    candidates = []
    for blk in blocks:
        x0, y0, x1, y1, text = blk[:5]
        if y0 > img_rect.y1 and (y0 - img_rect.y1) < 50:
            candidates.append((y0, text.strip()))
    if not candidates:
        return ""
    # Prefer a block that mentions Fig/Figure
    for _, txt in sorted(candidates):
        if re.search(r"\bFig(?:ure)?\b", txt, re.IGNORECASE):
            return txt
    # Fallback – closest block
    return sorted(candidates)[0][1]


def _parse_figure_number(caption: str) -> str:
    """Extract strings like 'Fig 23.19' or 'Figure 12' from a caption.
    Returns empty string if not found.
    """
    match = re.search(r"(Fig(?:ure)?\s*\d+[\.\d]*)", caption, re.IGNORECASE)
    return match.group(1).replace(" ", "_") if match else ""


def main() -> None:
    if not PDF_PATH.is_file():
        logger.error(f"PDF not found at {PDF_PATH}. Abort.")
        sys.exit(1)

    logger.info(f"Opening PDF: {PDF_PATH}")
    doc = fitz.open(str(PDF_PATH))
    manifest: List[Dict] = []

    total_pages = len(doc)
    logger.info(f"Document contains {total_pages} pages.")

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc.load_page(page_idx)
        img_list = page.get_images(full=True)
        if not img_list:
            continue

        for img_index, img in enumerate(img_list, start=1):
            xref = img[0]
            # Extract raw image bytes as PNG (preserve original resolution)
            try:
                pix = fitz.Pixmap(doc, xref)
                img_bytes = pix.tobytes("png")
            except Exception as exc:
                logger.warning(f"Failed to extract image {img_index} on page {page_num}: {exc}")
                continue

            img_name = f"img-robins-p{page_num:04d}-f{img_index:03d}.png"
            img_path = OUTPUT_DIR / img_name
            with open(img_path, "wb") as out_f:
                out_f.write(img_bytes)

            # Approximate image rectangle – may be None for some PDFs; handle gracefully
            try:
                rect = page.get_image_bbox(xref)
            except Exception:
                # Some images may not have a bounding box; continue without caption extraction
                rect = None
                logger.warning(f"Could not get bbox for image {img_index} on page {page_num}, proceeding without caption.")
            caption = _extract_caption(page, rect) if rect else ""
            fig_num = _parse_figure_number(caption)

            manifest.append(
                {
                    "image_id": img_name.rstrip(".png"),
                    "file_path": str(img_path),
                    "page_number": page_num,
                    "figure_number": fig_num,
                    "caption": caption,
                    "stain_type": "",
                    "magnification": "",
                    "organ_system": "",
                    "diagnostic_hallmarks": "",
                    "source_reference": f"Robbins 11e p.{page_num}",
                    "dpi": DPI,
                }
            )
            logger.info(f"Extracted {img_name} (page {page_num}, figure {img_index})")

    # Write manifest JSON – pretty printed for human readability
    with open(MANIFEST_PATH, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    logger.info(f"✅ Extraction complete – {len(manifest)} images saved.")
    logger.info(f"Manifest written to {MANIFEST_PATH}")
    logger.info(f"Log file located at {LOG_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Unexpected error during extraction")
        sys.exit(1)
