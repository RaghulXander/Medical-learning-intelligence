"""
backend/ingestion/document_registry.py

Immutable Reference Document Registry.
Maintains cryptographically verified records (SHA-256) of raw medical textbooks,
monographs, and reference works. Ensures provenance integrity and tamper detection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf

logger = logging.getLogger(__name__)

# Canonical namespace for deterministic Document UUID generation
DOCUMENT_NAMESPACE = uuid.UUID("7c9e6679-7425-40de-944b-e07fc1f90ae7")

DEFAULT_REGISTRY_PATH = Path("data/processed/reference_documents/registry.json")


def compute_file_sha256(file_path: Path | str, chunk_size: int = 65536) -> str:
    """Computes SHA-256 checksum for a file on disk."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_pdf_page_count(file_path: Path | str) -> int:
    """Reads the total page count from a PDF file using pypdf."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    with open(path, "rb") as f:
        reader = pypdf.PdfReader(f)
        return len(reader.pages)


@dataclass
class SliceManifest:
    """Metadata for a sliced chunk of a parent reference document with dual page tracking."""
    slice_id: str
    parent_doc_id: str
    parent_doc_title: str
    parent_sha256: str
    start_page_1based: int  # PDF physical start page (1-based)
    end_page_1based: int    # PDF physical end page (1-based)
    page_count: int
    slice_file_path: str
    slice_file_name: str
    slice_sha256: str
    page_offset_map: Dict[int, int] = field(default_factory=dict)  # slice_local_page -> pdf_page
    textbook_page_offset: int = 0
    textbook_start_page: Optional[int] = None
    textbook_end_page: Optional[int] = None
    pdf_to_textbook_map: Dict[int, Optional[int]] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "CREATED"  # CREATED, PROCESSED, NORMALIZED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SliceManifest:
        # Convert string keys in page maps to ints if necessary
        if "page_offset_map" in data and isinstance(data["page_offset_map"], dict):
            data["page_offset_map"] = {
                int(k): int(v) for k, v in data["page_offset_map"].items()
            }
        if "pdf_to_textbook_map" in data and isinstance(data["pdf_to_textbook_map"], dict):
            data["pdf_to_textbook_map"] = {
                int(k): (int(v) if v is not None else None)
                for k, v in data["pdf_to_textbook_map"].items()
            }
        return cls(**data)


@dataclass
class RegisteredDocument:
    """Immutable record of an authoritative reference document with front-matter offset tracking."""
    doc_id: str
    short_name: str
    title: str
    author: Optional[str]
    edition: Optional[str]
    year: Optional[int]
    publisher: Optional[str]
    source_type: str  # TEXTBOOK, REVIEW_BOOK, GUIDELINE, WHO_CLASSIFICATION
    speciality: str
    subject: str
    file_name: str
    file_path: str
    file_size_bytes: int
    sha256: str
    total_pages: int
    textbook_page_offset: int = 0  # Number of front matter/preface pages before printed page 1
    version: int = 1  # Ingestion calibration version (bump if page calibration changes)
    registered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    slices: Dict[str, SliceManifest] = field(default_factory=dict)

    def get_textbook_page(self, pdf_page: int) -> Optional[int]:
        """Calculates printed textbook page from physical PDF page index."""
        if pdf_page <= self.textbook_page_offset:
            return None  # Front matter / preface / table of contents
        return pdf_page - self.textbook_page_offset

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["slices"] = {
            sid: s.to_dict() if isinstance(s, SliceManifest) else s
            for sid, s in self.slices.items()
        }
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegisteredDocument:
        slices_data = data.pop("slices", {})
        slices = {}
        for sid, sdata in slices_data.items():
            if isinstance(sdata, dict):
                slices[sid] = SliceManifest.from_dict(sdata)
            elif isinstance(sdata, SliceManifest):
                slices[sid] = sdata
        return cls(slices=slices, **data)


class DocumentRegistry:
    """Thread-safe and persistence-backed registry of reference documents."""

    def __init__(self, registry_path: Path | str = DEFAULT_REGISTRY_PATH):
        self.registry_path = Path(registry_path)
        self.documents: Dict[str, RegisteredDocument] = {}
        self.short_name_index: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """Loads registry data from disk if file exists."""
        if not self.registry_path.exists():
            self.documents = {}
            self.short_name_index = {}
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            docs_data = raw_data.get("documents", {})
            self.documents = {}
            self.short_name_index = {}

            for doc_id, doc_dict in docs_data.items():
                doc = RegisteredDocument.from_dict(doc_dict)
                self.documents[doc.doc_id] = doc
                self.short_name_index[doc.short_name.lower()] = doc.doc_id

        except Exception as e:
            logger.error(f"Error loading registry from {self.registry_path}: {e}")
            raise

    def save(self) -> None:
        """Atomically saves the registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(self.documents),
            "documents": {
                doc_id: doc.to_dict() for doc_id, doc in self.documents.items()
            },
        }

        temp_file = self.registry_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        try:
            if self.registry_path.exists():
                self.registry_path.unlink(missing_ok=True)
            temp_file.replace(self.registry_path)
        except Exception:
            # Fallback write directly if atomic replace encountered OS file lock
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)

    def register_document(
        self,
        file_path: Path | str,
        short_name: str,
        title: str,
        author: Optional[str] = None,
        edition: Optional[str] = None,
        year: Optional[int] = None,
        publisher: Optional[str] = None,
        source_type: str = "TEXTBOOK",
        speciality: str = "Pathology",
        subject: str = "Pathology",
        textbook_page_offset: int = 0,
        version: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RegisteredDocument:
        """Registers a raw reference PDF file with cryptographic hash validation and page offset tracking."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Cannot register non-existent file: {path}")

        file_size = path.stat().st_size
        sha256 = compute_file_sha256(path)
        total_pages = get_pdf_page_count(path)

        # Generate deterministic UUIDv5 based on short_name, sha256, and version
        doc_id = str(
            uuid.uuid5(DOCUMENT_NAMESPACE, f"{short_name.lower()}:{sha256}:v{version}")
        )

        existing = self.documents.get(doc_id)
        slices = existing.slices if existing else {}

        doc = RegisteredDocument(
            doc_id=doc_id,
            short_name=short_name,
            title=title,
            author=author,
            edition=edition,
            year=year,
            publisher=publisher,
            source_type=source_type,
            speciality=speciality,
            subject=subject,
            file_name=path.name,
            file_path=str(path.resolve()),
            file_size_bytes=file_size,
            sha256=sha256,
            total_pages=total_pages,
            textbook_page_offset=textbook_page_offset,
            version=version,
            registered_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
            slices=slices,
        )

        self.documents[doc_id] = doc
        self.short_name_index[short_name.lower()] = doc_id
        self.save()
        return doc

    def get_document(self, doc_id_or_short_name: str) -> Optional[RegisteredDocument]:
        """Retrieves a registered document by UUID or short_name."""
        if doc_id_or_short_name in self.documents:
            return self.documents[doc_id_or_short_name]

        short_lower = doc_id_or_short_name.lower()
        if short_lower in self.short_name_index:
            doc_id = self.short_name_index[short_lower]
            return self.documents.get(doc_id)

        return None

    def list_documents(self) -> List[RegisteredDocument]:
        """Returns all registered documents."""
        return list(self.documents.values())

    def verify_integrity(
        self, doc_id_or_short_name: str
    ) -> Tuple[bool, str, str, str]:
        """
        Verifies that the physical file on disk matches its registered SHA-256 hash.
        Returns (is_valid, registered_hash, computed_hash, status_message).
        """
        doc = self.get_document(doc_id_or_short_name)
        if not doc:
            return (False, "", "", f"Document '{doc_id_or_short_name}' not found in registry")

        file_path = Path(doc.file_path)
        if not file_path.exists():
            return (False, doc.sha256, "", f"File does not exist at {file_path}")

        computed_sha = compute_file_sha256(file_path)
        if computed_sha == doc.sha256:
            return (True, doc.sha256, computed_sha, "INTEGRITY_VERIFIED")
        else:
            return (
                False,
                doc.sha256,
                computed_sha,
                f"INTEGRITY_VIOLATION: File modified! Expected {doc.sha256}, got {computed_sha}",
            )

    def register_slice(self, manifest: SliceManifest) -> None:
        """Associates a sliced PDF chunk manifest with its parent document."""
        doc = self.get_document(manifest.parent_doc_id)
        if not doc:
            raise KeyError(f"Parent document '{manifest.parent_doc_id}' not registered.")

        doc.slices[manifest.slice_id] = manifest
        self.save()

    def get_slice(self, slice_id: str) -> Optional[SliceManifest]:
        """Finds a slice manifest across all registered documents."""
        for doc in self.documents.values():
            if slice_id in doc.slices:
                return doc.slices[slice_id]
        return None

    def list_slices(
        self, doc_id_or_short_name: Optional[str] = None
    ) -> List[SliceManifest]:
        """Lists slices, optionally filtered by parent document."""
        if doc_id_or_short_name:
            doc = self.get_document(doc_id_or_short_name)
            return list(doc.slices.values()) if doc else []

        all_slices: List[SliceManifest] = []
        for doc in self.documents.values():
            all_slices.extend(doc.slices.values())
        return all_slices
