"""
Medical Exam AI — Ingestion & Reference Document Modules
"""

from backend.ingestion.docai_normalizer import (
    DocumentAINormalizer,
    NormalizedBlock,
    NormalizedDocumentSlice,
)
from backend.ingestion.document_registry import (
    DOCUMENT_NAMESPACE,
    DocumentRegistry,
    RegisteredDocument,
    SliceManifest,
    compute_file_sha256,
)
from backend.ingestion.gcp_docai_client import DocumentAIClient
from backend.ingestion.medical_normalizer import MedicalNormalizer, PageEvidenceBlock
from backend.ingestion.pdf_splitter import PDFSplitter
from backend.ingestion.quality_report import QualityReport, QualityReportGenerator
from backend.ingestion.universal_ingestor import UniversalQuestionIngestor

__all__ = [
    "DocumentRegistry",
    "RegisteredDocument",
    "SliceManifest",
    "compute_file_sha256",
    "DOCUMENT_NAMESPACE",
    "PDFSplitter",
    "DocumentAIClient",
    "DocumentAINormalizer",
    "NormalizedBlock",
    "NormalizedDocumentSlice",
    "MedicalNormalizer",
    "PageEvidenceBlock",
    "QualityReport",
    "QualityReportGenerator",
    "UniversalQuestionIngestor",
]
