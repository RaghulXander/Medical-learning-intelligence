"""
scripts/process_reference_documents.py

Document AI Processing, Structured Normalization, and Extraction Quality Audit CLI.
Processes sliced PDF chunks via Google Cloud Document AI Layout Parser (with offline mock fallback),
normalizes into domain blocks, generates quality reports, and asserts 100% provenance retention.

Usage:
  python scripts/process_reference_documents.py pilot
  python scripts/process_reference_documents.py process --slice robbins_review_p0001_p0015
  python scripts/process_reference_documents.py report --slice robbins_review_p0001_p0015
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion.docai_normalizer import DocumentAINormalizer
from backend.ingestion.document_registry import DocumentRegistry
from backend.ingestion.gcp_docai_client import DocumentAIClient
from backend.ingestion.medical_normalizer import MedicalNormalizer, PageEvidenceBlock
from backend.ingestion.pdf_splitter import PDFSplitter
from backend.ingestion.quality_report import QualityReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("process_reference_documents")


def process_single_slice(
    slice_id: str,
    registry: DocumentRegistry,
    docai_client: DocumentAIClient,
    normalizer: DocumentAINormalizer,
    med_normalizer: MedicalNormalizer,
    report_gen: QualityReportGenerator,
    force_mock: bool = False,
) -> None:
    """End-to-end processing of a single slice: Layout Parse -> Normalize -> Medical Curation -> Quality Report."""
    manifest = registry.get_slice(slice_id)
    if not manifest:
        logger.error(f"Slice manifest '{slice_id}' not found in registry.")
        return

    slice_path = Path(manifest.slice_file_path)
    if not slice_path.exists():
        logger.error(f"Slice PDF does not exist at {slice_path}")
        return

    logger.info(f"⚡ [1/4] Parsing layout for slice '{slice_id}' ({manifest.page_count} pages)...")
    raw_docai = docai_client.process_slice_online(
        slice_pdf_path=slice_path,
        manifest=manifest,
        force_mock=force_mock,
    )

    logger.info(f"🧩 [2/4] Normalizing Document AI layout into structured domain blocks...")
    normalized_slice = normalizer.normalize(
        raw_docai_data=raw_docai,
        manifest=manifest,
    )
    logger.info(
        f"   Normalized {normalized_slice.total_blocks} blocks "
        f"({normalized_slice.summary_stats.get('heading_count')} headings, "
        f"{normalized_slice.summary_stats.get('paragraph_count')} paragraphs, "
        f"{normalized_slice.summary_stats.get('table_count')} tables)"
    )

    logger.info(f"🩺 [3/4] Curating page-level evidence blocks & two-column reading flow...")
    evidence_blocks = med_normalizer.normalize_slice(normalized_slice)
    logger.info(f"   Generated {len(evidence_blocks)} page-level evidence blocks (PDF & textbook calibrated)")

    logger.info(f"📊 [4/4] Auditing extraction quality and provenance retention...")
    report = report_gen.generate_report(
        normalized_slice=normalized_slice,
        registry=registry,
    )

    status_icon = "✅" if report.provenance_verified else "❌"
    logger.info(
        f"{status_icon} Quality Report Generated: Integrity Score = {report.provenance_integrity_score * 100:.1f}%, "
        f"Avg Confidence = {report.average_confidence * 100:.2f}%, Words = {report.total_words:,}"
    )


def cmd_process(args: argparse.Namespace) -> None:
    """Processes a specific slice by slice_id."""
    registry = DocumentRegistry()
    docai_client = DocumentAIClient()
    normalizer = DocumentAINormalizer()
    med_normalizer = MedicalNormalizer()
    report_gen = QualityReportGenerator()

    process_single_slice(
        slice_id=args.slice,
        registry=registry,
        docai_client=docai_client,
        normalizer=normalizer,
        med_normalizer=med_normalizer,
        report_gen=report_gen,
        force_mock=args.mock,
    )


def cmd_book(args: argparse.Namespace) -> None:
    """Processes multiple sequential chunks of a book (e.g. --doc robbins_review --pages-per-chunk 15 --max-chunks 5)."""
    registry = DocumentRegistry()
    splitter = PDFSplitter(registry=registry)
    docai_client = DocumentAIClient()
    normalizer = DocumentAINormalizer()
    med_normalizer = MedicalNormalizer()
    report_gen = QualityReportGenerator()

    doc = registry.get_document(args.doc)
    if not doc:
        logger.error(f"Document '{args.doc}' not found in registry.")
        return

    # Respect GCP online layout parser ceiling (<= 15 pages per request)
    raw_pages_per_chunk = args.pages_per_chunk or args.pages_per_slice or 15
    if raw_pages_per_chunk > 15:
        logger.warning(
            f"Requested {raw_pages_per_chunk} pages per chunk exceeds GCP Document AI online layout parser limit (15). Clamping to 15."
        )
    pages_per_chunk = min(raw_pages_per_chunk, 15)

    max_chunks = args.max_chunks or args.chunks or 9999
    start_offset = args.start_page or 1

    logger.info(
        f"🚀 Slicing & processing '{doc.title}' in {pages_per_chunk}-page chunks "
        f"(Max chunks: {'All' if max_chunks >= 9999 else max_chunks}, Start page: {start_offset})..."
    )
    slices = splitter.create_pilot_chunks(
        doc_id_or_short_name=doc.doc_id,
        max_slices=max_chunks,
        pages_per_slice=pages_per_chunk,
        start_offset_1based=start_offset,
    )

    logger.info(f"Created {len(slices)} chunks. Commencing Document AI & Medical Normalization...")
    for idx, manifest in enumerate(slices, start=1):
        logger.info(f"\n--- Chunk {idx}/{len(slices)}: {manifest.slice_id} (PDF Pages {manifest.start_page_1based}..{manifest.end_page_1based}) ---")
        process_single_slice(
            slice_id=manifest.slice_id,
            registry=registry,
            docai_client=docai_client,
            normalizer=normalizer,
            med_normalizer=med_normalizer,
            report_gen=report_gen,
            force_mock=args.mock,
        )


def cmd_pilot(args: argparse.Namespace) -> None:
    """One-shot command: registers raw books, extracts 15-page pilot slices, processes and reports."""
    from scripts.manage_reference_documents import cmd_register

    logger.info("🚀 Starting Pilot Reference Document Preparation Pipeline...")
    registry = DocumentRegistry()

    # 1. Register raw documents if needed
    cmd_register(argparse.Namespace(file=None))
    registry.load()

    splitter = PDFSplitter(registry=registry)
    docai_client = DocumentAIClient()
    normalizer = DocumentAINormalizer()
    med_normalizer = MedicalNormalizer()
    report_gen = QualityReportGenerator()

    docs = registry.list_documents()
    if not docs:
        logger.error("No documents found in raw directory. Check data/raw/reference_documents/")
        return

    logger.info(f"Found {len(docs)} registered reference document(s). Preparing pilot slices (15 pages each)...")

    for doc in docs:
        logger.info(f"\n=======================================================")
        logger.info(f"Processing Pilot Slice for: {doc.title} ({doc.short_name})")
        logger.info(f"=======================================================")

        # Create a 15-page pilot slice starting from page 1
        end_page = min(15, doc.total_pages)
        manifest = splitter.split_slice(
            doc_id_or_short_name=doc.doc_id,
            start_page_1based=1,
            end_page_1based=end_page,
            slice_suffix="pilot",
        )

        process_single_slice(
            slice_id=manifest.slice_id,
            registry=registry,
            docai_client=docai_client,
            normalizer=normalizer,
            med_normalizer=med_normalizer,
            report_gen=report_gen,
            force_mock=args.mock,
        )

    logger.info("\n🎉 Pilot processing complete for all reference documents!")
    logger.info("Outputs available in:")
    logger.info("  - Slices:          data/processed/reference_documents/slices/")
    logger.info("  - Normalized:      data/processed/reference_documents/normalized/")
    logger.info("  - Evidence Blocks: data/processed/reference_documents/evidence_blocks/")
    logger.info("  - Reports:         data/processed/reference_documents/reports/")


def main():
    parser = argparse.ArgumentParser(description="Document AI Processing & Quality Reporting CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # process
    proc_parser = subparsers.add_parser("process", help="Process a single slice")
    proc_parser.add_argument("--slice", required=True, help="Slice ID (e.g. robbins_review_p0001_p0015)")
    proc_parser.add_argument("--mock", action="store_true", default=False, help="Force mock layout generator")
    proc_parser.set_defaults(func=cmd_process)

    # pilot
    pilot_parser = subparsers.add_parser("pilot", help="Run end-to-end pilot processing on all raw reference books")
    pilot_parser.add_argument("--mock", action="store_true", default=False, help="Force mock layout generator")
    pilot_parser.set_defaults(func=cmd_pilot)

    # book
    book_parser = subparsers.add_parser(
        "book",
        help="Process multiple sequential chunks of a registered book (strictly <= 15 pages per chunk)",
    )
    book_parser.add_argument(
        "--doc",
        required=True,
        help="Document ID or short_name (e.g. robbins_review or robbins_pathologic_basis_11th)",
    )
    book_parser.add_argument(
        "--pages-per-chunk",
        type=int,
        default=15,
        help="Number of PDF pages per chunk/Document AI request (default: 15, max: 15)",
    )
    book_parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Maximum number of sequential chunks to process (e.g. --max-chunks 20; default: all chunks)",
    )
    book_parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Starting 1-based PDF physical page (default: 1)",
    )
    book_parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Force mock layout generator (for offline / CI testing)",
    )
    # Aliases for backwards compatibility
    book_parser.add_argument("--chunks", type=int, default=None, help=argparse.SUPPRESS)
    book_parser.add_argument("--pages-per-slice", type=int, default=None, help=argparse.SUPPRESS)
    book_parser.set_defaults(func=cmd_book)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
