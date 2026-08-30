"""
scripts/manage_reference_documents.py

CLI Management Tool for Authoritative Reference Documents.
Registers raw textbooks, verifies tamper-detection checksums, and creates pilot slices
with strict 1-based original page offset preservation.

Usage:
  python scripts/manage_reference_documents.py register
  python scripts/manage_reference_documents.py verify
  python scripts/manage_reference_documents.py list
  python scripts/manage_reference_documents.py split --doc robbins_review --start 1 --end 15
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion.document_registry import DocumentRegistry
from backend.ingestion.pdf_splitter import PDFSplitter
from backend.ingestion.provenance_manifest import ProvenanceManifestAuditor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("manage_reference_documents")

RAW_DOCS_DIR = Path("data/raw/reference_documents")

KNOWN_DOCUMENTS = [
    {
        "file_name": "Robbins and Cotran Review of Pathology.pdf",
        "short_name": "robbins_review",
        "title": "Robbins and Cotran Review of Pathology",
        "author": "Edward C. Klatt, Vinay Kumar",
        "edition": "4th Edition",
        "year": 2014,
        "publisher": "Elsevier Saunders",
        "source_type": "REVIEW_BOOK",
        "textbook_page_offset": 5,  # PDF Page 11 = Textbook Page 6
    },
    {
        "file_name": "Robbins_and_Cotran_Pathologic_Basis_of_Disease_11th_Edition.pdf",
        "short_name": "robbins_pathologic_basis_11th",
        "title": "Robbins & Cotran Pathologic Basis of Disease",
        "author": "Vinay Kumar, Abul K. Abbas, Jon C. Aster",
        "edition": "11th Edition",
        "year": 2024,
        "publisher": "Elsevier",
        "source_type": "TEXTBOOK",
        "textbook_page_offset": 16,  # PDF Page 17 = Textbook Page 1
    },
    {
        "file_name": "Sternberg's diagnostic surgical pathology review 2nd Ed.pdf",
        "short_name": "sternberg_review_2nd",
        "title": "Sternberg's Diagnostic Surgical Pathology Review",
        "author": "Pier Luigi Di Patre, Carter J. Witkowski",
        "edition": "2nd Edition",
        "year": 2015,
        "publisher": "Wolters Kluwer",
        "source_type": "REVIEW_BOOK",
        "textbook_page_offset": 12,  # PDF Page 13 = Textbook Page 1
    },
]


def cmd_register(args: argparse.Namespace) -> None:
    """Registers raw PDF files from data/raw/reference_documents/ into the registry."""
    registry = DocumentRegistry()
    registered_count = 0
    requested_known_doc = getattr(args, "doc", None)

    for doc_meta in KNOWN_DOCUMENTS:
        if requested_known_doc and doc_meta["short_name"] != requested_known_doc:
            continue
        pdf_path = RAW_DOCS_DIR / doc_meta["file_name"]
        if not pdf_path.exists():
            logger.warning(f"File not found: {pdf_path}. Skipping.")
            continue

        logger.info(f"Registering '{doc_meta['title']}' from {pdf_path.name}...")
        doc = registry.register_document(
            file_path=pdf_path,
            short_name=doc_meta["short_name"],
            title=doc_meta["title"],
            author=doc_meta["author"],
            edition=doc_meta["edition"],
            year=doc_meta["year"],
            publisher=doc_meta["publisher"],
            source_type=doc_meta["source_type"],
            textbook_page_offset=doc_meta.get("textbook_page_offset", 0),
            rights_status=getattr(args, "rights_status", "UNVERIFIED"),
            rights_basis=getattr(args, "rights_basis", None),
        )
        logger.info(
            f"✅ Registered: {doc.short_name} -> ID: {doc.doc_id} (Pages: {doc.total_pages}, Front-matter offset: {doc.textbook_page_offset})"
        )
        registered_count += 1

    # Also register any custom file passed via --file
    if getattr(args, "file", None):
        custom_path = Path(args.file)
        if custom_path.exists():
            short_name = args.short_name or custom_path.stem.lower().replace(" ", "_")
            doc = registry.register_document(
                file_path=custom_path,
                short_name=short_name,
                title=args.title or custom_path.stem,
                source_type=args.source_type or "TEXTBOOK",
                rights_status=getattr(args, "rights_status", "UNVERIFIED"),
                rights_basis=getattr(args, "rights_basis", None),
            )
            logger.info(f"✅ Registered custom file: {doc.short_name} (Pages: {doc.total_pages})")
            registered_count += 1

    logger.info(f"Registration complete. Total registered documents: {len(registry.documents)}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verifies cryptographic SHA-256 hashes of all registered documents."""
    registry = DocumentRegistry()
    docs = registry.list_documents()
    if not docs:
        logger.warning("Registry is empty. Run 'register' first.")
        return

    logger.info(f"Verifying integrity for {len(docs)} registered document(s)...")
    all_ok = True

    for doc in docs:
        is_valid, expected, actual, status = registry.verify_integrity(doc.doc_id)
        if is_valid:
            logger.info(f"✅ [VERIFIED] {doc.short_name} ({doc.file_name}): SHA-256 matches registered hash.")
        else:
            logger.error(f"❌ [INTEGRITY VIOLATION] {doc.short_name}: {status}")
            all_ok = False

    if all_ok:
        logger.info("🎉 All reference documents passed cryptographic integrity verification!")
    else:
        logger.error("⚠️ One or more documents failed integrity check.")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """Lists registered reference documents and their active slices."""
    registry = DocumentRegistry()
    docs = registry.list_documents()
    if not docs:
        print("No reference documents registered. Run 'python scripts/manage_reference_documents.py register'.")
        return

    print("\n" + "=" * 80)
    print("IMMUTABLE REFERENCE DOCUMENT REGISTRY")
    print("=" * 80)
    for doc in docs:
        print(f"\n📘 [{doc.short_name}] {doc.title} ({doc.edition or 'Standard'})")
        print(f"   ID:          {doc.doc_id}")
        print(f"   Total Pages: {doc.total_pages} pages")
        print(f"   File Size:   {doc.file_size_bytes / (1024 * 1024):.2f} MB")
        print(f"   SHA-256:     {doc.sha256}")
        print(f"   Slices:      {len(doc.slices)} created")
        for sid, s in doc.slices.items():
            print(f"      - {sid}: Pages {s.start_page_1based}..{s.end_page_1based} ({s.page_count} pages)")
    print("\n" + "=" * 80)


def cmd_split(args: argparse.Namespace) -> None:
    """Splits a registered document into a pilot chunk with 1-based page offset preservation."""
    registry = DocumentRegistry()
    splitter = PDFSplitter(registry=registry)

    doc = registry.get_document(args.doc)
    if not doc:
        logger.error(f"Document '{args.doc}' not found in registry. Run 'register' or 'list' first.")
        sys.exit(1)

    start = int(args.start)
    end = int(args.end)
    logger.info(f"Extracting slice from '{doc.short_name}' (pages {start} to {end})...")

    manifest = splitter.split_slice(
        doc_id_or_short_name=doc.doc_id,
        start_page_1based=start,
        end_page_1based=end,
        slice_suffix=args.suffix,
    )

    logger.info(f"✅ Slice created successfully: {manifest.slice_id}")
    logger.info(f"   Slice PDF:  {manifest.slice_file_path}")
    logger.info(f"   SHA-256:    {manifest.slice_sha256}")
    logger.info(f"   Page Map:   {len(manifest.page_offset_map)} page mappings stored in manifest.")


def cmd_audit(args: argparse.Namespace) -> None:
    """Audits book provenance manifest and evaluates the hard embedding gate."""
    registry = DocumentRegistry()
    auditor = ProvenanceManifestAuditor()
    pages_per_chunk = getattr(args, "pages_per_chunk", 15)

    manifest = auditor.generate_manifest(
        doc_id_or_short_name=args.doc,
        registry=registry,
        pages_per_chunk=pages_per_chunk,
    )

    status_icon = "✅" if manifest.is_ready_for_embedding else "❌"
    logger.info(f"\n=======================================================")
    logger.info(f"{status_icon} Provenance Audit: {manifest.title} ({manifest.short_name})")
    logger.info(f"=======================================================")
    logger.info(f"   Status:                 {manifest.status}")
    logger.info(f"   Total Physical Pages:   {manifest.total_pdf_pages}")
    logger.info(f"   Completed Chunks:       {manifest.completed_chunks} / {manifest.expected_chunks}")
    logger.info(f"   Missing Pages:          {len(manifest.missing_pages)}")
    logger.info(f"   Duplicate Pages:        {len(manifest.duplicate_pages)}")
    logger.info(f"   Evidence Blocks:        {manifest.total_evidence_blocks:,}")
    logger.info(f"   Total Words:            {manifest.total_words:,}")
    logger.info(f"   Embedding Gate:         {'ALLOWED (READY)' if manifest.is_ready_for_embedding else 'BLOCKED (STOP)'}")
    logger.info(f"   Manifest Report:        data/processed/reference_documents/provenance_manifests/{manifest.short_name}_provenance_manifest.md")

    if args.enforce and not manifest.is_ready_for_embedding:
        logger.error("🛑 Hard gate enforcement triggered: document is not ready for embedding.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Reference Document Registry & Slicing Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # register
    reg_parser = subparsers.add_parser("register", help="Register raw reference PDFs")
    reg_parser.add_argument("--file", help="Optional path to custom PDF file")
    reg_parser.add_argument(
        "--doc",
        choices=tuple(doc["short_name"] for doc in KNOWN_DOCUMENTS),
        help="Register only one known local reference document",
    )
    reg_parser.add_argument("--short-name", help="Short name for custom PDF")
    reg_parser.add_argument("--title", help="Title for custom PDF")
    reg_parser.add_argument("--source-type", default="TEXTBOOK", help="Source type (TEXTBOOK, REVIEW_BOOK, etc.)")
    reg_parser.add_argument(
        "--rights-status",
        choices=("AUTHORIZED", "UNVERIFIED", "REJECTED"),
        default="UNVERIFIED",
        help="Whether you have rights to process the supplied documents",
    )
    reg_parser.add_argument(
        "--rights-basis",
        help="Private audit note such as purchased copy, institutional licence, or public domain",
    )
    reg_parser.set_defaults(func=cmd_register)

    # verify
    ver_parser = subparsers.add_parser("verify", help="Verify SHA-256 checksums")
    ver_parser.set_defaults(func=cmd_verify)

    # list
    list_parser = subparsers.add_parser("list", help="List registered documents and slices")
    list_parser.set_defaults(func=cmd_list)

    # split
    split_parser = subparsers.add_parser("split", help="Extract a pilot slice from a registered document")
    split_parser.add_argument("--doc", required=True, help="Document ID or short_name")
    split_parser.add_argument("--start", type=int, default=1, help="1-based start page")
    split_parser.add_argument("--end", type=int, default=15, help="1-based end page")
    split_parser.add_argument("--suffix", default=None, help="Optional suffix for slice ID")
    split_parser.set_defaults(func=cmd_split)

    # audit
    audit_parser = subparsers.add_parser("audit", help="Audit book provenance manifest and evaluate embedding gate")
    audit_parser.add_argument("--doc", required=True, help="Document ID or short_name (e.g. robbins_review)")
    audit_parser.add_argument("--pages-per-chunk", type=int, default=15, help="Pages per chunk (default: 15)")
    audit_parser.add_argument("--enforce", action="store_true", default=False, help="Exit with non-zero code if gate fails")
    audit_parser.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
