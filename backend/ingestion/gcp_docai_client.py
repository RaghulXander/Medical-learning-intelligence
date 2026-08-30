"""
backend/ingestion/gcp_docai_client.py

Google Cloud Document AI Layout Parser Client.
Supports online (<=15 pages) and batch processing pipelines with automatic page-limit
enforcement, GCS integration, and deterministic offline mock layout parsing for CI/dev.
"""

from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf

from backend.core.config import get_settings
from backend.ingestion.document_registry import SliceManifest

logger = logging.getLogger(__name__)

DEFAULT_RAW_DOCAI_DIR = Path("data/processed/reference_documents/raw_docai")


class DocumentAIClient:
    """Client for Google Cloud Document AI Layout Parser with offline fallback."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        processor_id: Optional[str] = None,
        raw_output_dir: Path | str = DEFAULT_RAW_DOCAI_DIR,
    ):
        settings = get_settings()
        self.project_id = project_id or settings.gcp_project_id
        self.location = location or settings.gcp_location
        self.processor_id = processor_id or settings.gcp_processor_id
        self.max_online_pages = settings.docai_max_online_pages
        self.mock_fallback = settings.docai_mock_fallback
        self.raw_output_dir = Path(raw_output_dir)
        self.raw_output_dir.mkdir(parents=True, exist_ok=True)

        self._processor_name = (
            f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
        )

    def process_slice_online(
        self,
        slice_pdf_path: Path | str,
        manifest: Optional[SliceManifest] = None,
        force_mock: bool = False,
    ) -> Dict[str, Any]:
        """
        Parses a PDF slice using Document AI online Layout Parser.
        Enforces maximum online page count (<= 15 pages).
        """
        path = Path(slice_pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF slice not found at {path}")

        # Check page count and size limits
        reader = pypdf.PdfReader(str(path))
        page_count = len(reader.pages)
        file_size_mb = path.stat().st_size / (1024 * 1024)

        if page_count > self.max_online_pages:
            raise ValueError(
                f"Slice exceeds Document AI online limit of {self.max_online_pages} pages (has {page_count} pages). "
                "Use PDFSplitter to create smaller chunks or dispatch to batch processing."
            )
        if file_size_mb > 20.0:
            raise ValueError(
                f"Slice exceeds Document AI online size limit of 20MB (size is {file_size_mb:.2f}MB)."
            )

        slice_id = manifest.slice_id if manifest else path.stem
        raw_json_path = self.raw_output_dir / f"{slice_id}_docai.json"

        if not force_mock:
            try:
                result_dict = self._call_gcp_documentai(path)
                with open(raw_json_path, "w", encoding="utf-8") as f:
                    json.dump(result_dict, f, indent=2, ensure_ascii=False)
                return result_dict
            except Exception as e:
                logger.warning(
                    f"GCP Document AI API call failed: {e}. Checking mock fallback..."
                )
                if not self.mock_fallback:
                    raise

        # Generate realistic offline layout representation
        result_dict = self._generate_mock_layout_doc(path, reader, manifest)
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        return result_dict

    def _call_gcp_documentai(self, pdf_path: Path) -> Dict[str, Any]:
        """Performs live synchronous RPC call to Google Cloud Document AI Layout Parser."""
        try:
            from google.api_core.client_options import ClientOptions
            from google.cloud import documentai
        except ImportError:
            raise RuntimeError(
                "google-cloud-documentai is not installed in the current environment."
            )

        opts = ClientOptions(
            api_endpoint=f"{self.location}-documentai.googleapis.com"
        )

        creds = None
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and Path(creds_path).exists():
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(creds_path)
            client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=creds)
        else:
            client = documentai.DocumentProcessorServiceClient(client_options=opts)

        with open(pdf_path, "rb") as f:
            content = f.read()

        raw_document = documentai.RawDocument(
            content=content, mime_type="application/pdf"
        )
        request = documentai.ProcessRequest(
            name=self._processor_name, raw_document=raw_document
        )

        response = client.process_document(request=request)
        document = response.document
        doc_json_str = documentai.Document.to_json(document)
        return json.loads(doc_json_str)

    def _generate_mock_layout_doc(
        self,
        pdf_path: Path,
        reader: pypdf.PdfReader,
        manifest: Optional[SliceManifest],
    ) -> Dict[str, Any]:
        """
        Synthesizes a compliant Google Cloud Document AI Document JSON structure
        from PDF page text for offline execution and tests.
        """
        full_text_parts: List[str] = []
        pages_data: List[Dict[str, Any]] = []
        current_offset = 0

        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            # Clean up whitespace
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            if not lines:
                lines = [f"[Page {page_idx + 1} Content]"]

            page_start_offset = current_offset
            page_paragraphs: List[Dict[str, Any]] = []
            page_blocks: List[Dict[str, Any]] = []
            page_tables: List[Dict[str, Any]] = []
            page_visual_elements: List[Dict[str, Any]] = []

            for line_idx, line in enumerate(lines):
                line_start = current_offset
                full_text_parts.append(line + "\n")
                current_offset += len(line) + 1
                line_end = current_offset - 1

                is_heading = (
                    len(line) < 80
                    and (
                        line.isupper()
                        or line.startswith("Chapter")
                        or line.startswith("Section")
                        or (line.endswith(":") and len(line) < 50)
                    )
                )

                # Normalized bounding box coordinates [ymin, xmin, ymax, xmax]
                y_min = max(0.05, min(0.90, (line_idx + 1) / (len(lines) + 2)))
                y_max = min(0.95, y_min + 0.04)

                block_type = "heading" if is_heading else "paragraph"
                elem_dict = {
                    "layout": {
                        "textAnchor": {
                            "textSegments": [
                                {
                                    "startIndex": str(line_start),
                                    "endIndex": str(line_end),
                                }
                            ]
                        },
                        "confidence": 0.96 if is_heading else 0.92,
                        "boundingPoly": {
                            "normalizedVertices": [
                                {"x": 0.1, "y": y_min},
                                {"x": 0.9, "y": y_min},
                                {"x": 0.9, "y": y_max},
                                {"x": 0.1, "y": y_max},
                            ]
                        },
                    },
                    "type": block_type,
                }

                if is_heading:
                    page_blocks.append(elem_dict)
                else:
                    page_paragraphs.append(elem_dict)

            # Synthesize table if page mentions "Table" or "Summary"
            if any("table" in l.lower() or "summary" in l.lower() for l in lines):
                table_elem = {
                    "layout": {
                        "confidence": 0.90,
                        "boundingPoly": {
                            "normalizedVertices": [
                                {"x": 0.1, "y": 0.5},
                                {"x": 0.9, "y": 0.5},
                                {"x": 0.9, "y": 0.8},
                                {"x": 0.1, "y": 0.8},
                            ]
                        },
                    },
                    "headerRows": [
                        {
                            "cells": [
                                {
                                    "layout": {
                                        "textAnchor": {
                                            "content": "Feature / Marker"
                                        }
                                    }
                                },
                                {
                                    "layout": {
                                        "textAnchor": {
                                            "content": "Diagnostic Finding"
                                        }
                                    }
                                },
                            ]
                        }
                    ],
                    "bodyRows": [
                        {
                            "cells": [
                                {
                                    "layout": {
                                        "textAnchor": {
                                            "content": "Morphology / IHC"
                                        }
                                    }
                                },
                                {
                                    "layout": {
                                        "textAnchor": {
                                            "content": "Positive / Specific expression"
                                        }
                                    }
                                },
                            ]
                        }
                    ],
                }
                page_tables.append(table_elem)

            page_dict = {
                "pageNumber": page_idx + 1,
                "dimension": {"width": 612.0, "height": 792.0, "unit": "point"},
                "paragraphs": page_paragraphs,
                "blocks": page_blocks,
                "tables": page_tables,
                "visualElements": page_visual_elements,
            }
            pages_data.append(page_dict)

        full_text = "".join(full_text_parts)

        return {
            "text": full_text,
            "pages": pages_data,
            "mimeType": "application/pdf",
            "metadata": {
                "mock_generated": True,
                "source_file": pdf_path.name,
                "slice_id": manifest.slice_id if manifest else pdf_path.stem,
            },
        }
