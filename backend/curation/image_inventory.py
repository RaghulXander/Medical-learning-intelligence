"""
backend/curation/image_inventory.py

Milestone 18A: Immutable Portable Image Inventory Engine.
Collects deterministic metadata, cryptographic hashes, dimensions,
entropy, and duplicate clusters for all extracted reference images without
modifying or deleting any underlying raw file.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import struct
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Master document hashes from registered reference document provenance
ROBBINS_11TH_SHA256 = "c43661f8d57ee7a29382d030a42620d270d7cb90f52c32817fe6bebae5e10129"
ROBBINS_REVIEW_SHA256 = "fa8331f82e0473e047f3ad5b78000492cb4f55ef36ef00994fef40d433b006c6"
STERNBERG_REVIEW_SHA256 = "b3371948e14c22c9749d5583cc16e1e5bff9b7698c802eeeeac9bb8619c734ba"

PROVENANCE_PREFIX_MAP = {
    "img-robins": ("robbins_pathologic_basis_11th", ROBBINS_11TH_SHA256, 16),
    "img-robreview": ("robbins_review", ROBBINS_REVIEW_SHA256, 5),
    "img-sternberg": ("sternberg_review_2nd", STERNBERG_REVIEW_SHA256, 14),
}


@dataclass
class ImageRecord:
    """Immutable metadata record for an individual extracted image asset."""
    extraction_id: str
    filename: str
    relative_path: str
    source_short_name: str
    source_document_hash: str
    pdf_page: Optional[int]
    textbook_page: Optional[int]
    figure_index: Optional[int]
    figure_label: Optional[str]
    file_size_bytes: int
    sha256: str
    pixel_hash: str
    width: int
    height: int
    aspect_ratio: float
    pixel_area: int
    bit_depth: int
    color_type: int
    color_mode: str
    has_alpha: bool
    is_corrupt: bool
    entropy: float
    blank_score: float
    is_exact_duplicate: bool = False
    duplicate_cluster_id: Optional[str] = None
    duplicate_count: int = 1
    duplicate_index: int = 0
    is_canonical: bool = True
    extractor_name: str = "scripts/extract_all_reference_images.py"
    extractor_version: str = "1.0.0"
    inventoried_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImageInventoryEngine:
    """
    Scans, inspects, hashes, and profiles extracted book images
    producing an immutable, portable inventory manifest.
    """

    def __init__(self, image_dir: Path | str):
        self.image_dir = Path(image_dir)
        if not self.image_dir.exists():
            raise FileNotFoundError(f"Image directory not found: {self.image_dir}")

    @staticmethod
    def compute_entropy(data: bytes) -> float:
        """Calculates Shannon entropy in bits per byte (0.0 to 8.0)."""
        if not data:
            return 0.0
        byte_counts = [0] * 256
        for b in data:
            byte_counts[b] += 1
        total = len(data)
        entropy = 0.0
        for count in byte_counts:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return round(entropy, 4)

    @staticmethod
    def parse_filename_provenance(filename: str) -> Tuple[str, str, Optional[int], Optional[int], Optional[int]]:
        """
        Parses source short name, master hash, physical PDF page, calculated printed textbook page,
        and figure index from filename format: {prefix}-p{page:04d}-f{fig:03d}.png
        """
        for prefix, (source_name, source_hash, offset) in PROVENANCE_PREFIX_MAP.items():
            pattern = rf"^{prefix}-p(\d{{4}})-f(\d{{3}})\.png$"
            match = re.match(pattern, filename)
            if match:
                pdf_page = int(match.group(1))
                fig_idx = int(match.group(2))
                textbook_page = pdf_page - offset if pdf_page > offset else None
                return source_name, source_hash, pdf_page, textbook_page, fig_idx

        # Generic fallback
        match = re.match(r"^img-[a-z0-9]+-p(\d{4})-f(\d{3})\.png$", filename)
        if match:
            pdf_page = int(match.group(1))
            fig_idx = int(match.group(2))
            return "unknown_reference_doc", ROBBINS_11TH_SHA256, pdf_page, None, fig_idx
        return "unknown_reference_doc", ROBBINS_11TH_SHA256, None, None, None

    @staticmethod
    def parse_png_header(data: bytes) -> Tuple[int, int, int, int, str, bool]:
        """
        Parses PNG IHDR header bytes safely using struct.
        Returns: (width, height, bit_depth, color_type, color_mode, has_alpha)
        """
        if len(data) < 29 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid PNG signature")

        magic, length, chunk_type, w, h, bit_depth, color_type = struct.unpack(">8sI4sIIBB", data[:26])
        if chunk_type != b"IHDR":
            raise ValueError("First PNG chunk is not IHDR")

        # Color type mapping:
        # 0: Grayscale, 2: RGB, 3: Palette, 4: Grayscale + Alpha, 6: RGBA
        color_modes = {
            0: "L (Grayscale)",
            2: "RGB",
            3: "P (Palette)",
            4: "LA (Grayscale+Alpha)",
            6: "RGBA",
        }
        color_mode = color_modes.get(color_type, f"Unknown ({color_type})")
        has_alpha = color_type in (4, 6)

        return w, h, bit_depth, color_type, color_mode, has_alpha

    def inspect_image_file(self, file_path: Path) -> ImageRecord:
        """Inspects a single image file and builds its immutable ImageRecord."""
        filename = file_path.name
        rel_path = str(file_path.relative_to(self.image_dir.parent)).replace("\\", "/")

        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        file_size = len(raw_bytes)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Parse filename provenance
        source_short_name, source_doc_hash, pdf_page, textbook_page, fig_idx = self.parse_filename_provenance(filename)
        extraction_id = f"ext-{filename.rstrip('.png')}"
        fig_label = f"Figure {fig_idx}" if fig_idx is not None else None

        # Try parsing PNG dimensions
        is_corrupt = False
        width, height, bit_depth, color_type = 0, 0, 0, 0
        color_mode = "Unknown"
        has_alpha = False
        try:
            width, height, bit_depth, color_type, color_mode, has_alpha = self.parse_png_header(raw_bytes)
        except Exception as e:
            logger.warning(f"Corrupt PNG header for {filename}: {e}")
            is_corrupt = True

        aspect_ratio = round(width / height, 4) if height > 0 else 0.0
        pixel_area = width * height

        # Compute entropy
        entropy = self.compute_entropy(raw_bytes)

        # Blank score calculation (heuristics: tiny file size relative to area or very low entropy)
        blank_score = 0.0
        if is_corrupt:
            blank_score = 1.0
        elif pixel_area > 0:
            bytes_per_pixel = file_size / pixel_area
            # Extremely low bytes-per-pixel (<0.02) with low entropy indicates nearly uniform/blank content
            if bytes_per_pixel < 0.02 and entropy < 2.0:
                blank_score = 0.95
            elif pixel_area < 25:  # e.g. 3x4 pixels
                blank_score = 0.90
            elif entropy < 1.0:
                blank_score = 0.99

        # Approximate pixel hash: truncated sha256 of header + size + entropy
        pixel_hash = hashlib.sha256(f"{width}:{height}:{color_type}:{file_size}:{entropy}".encode()).hexdigest()[:16]

        return ImageRecord(
            extraction_id=extraction_id,
            filename=filename,
            relative_path=rel_path,
            source_short_name=source_short_name,
            source_document_hash=source_doc_hash,
            pdf_page=pdf_page,
            textbook_page=textbook_page,
            figure_index=fig_idx,
            figure_label=fig_label,
            file_size_bytes=file_size,
            sha256=sha256,
            pixel_hash=pixel_hash,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            pixel_area=pixel_area,
            bit_depth=bit_depth,
            color_type=color_type,
            color_mode=color_mode,
            has_alpha=has_alpha,
            is_corrupt=is_corrupt,
            entropy=entropy,
            blank_score=blank_score,
        )

    def run_inventory(self) -> Tuple[List[ImageRecord], Dict[str, Any]]:
        """
        Executes full inventory across all images in the directory,
        resolves exact duplicates, and generates an aggregate inventory summary.
        """
        image_files = sorted(self.image_dir.glob("*.png"))
        logger.info(f"🔍 Inspecting {len(image_files):,} image files in {self.image_dir}...")

        records: List[ImageRecord] = []
        sha_groups: Dict[str, List[ImageRecord]] = {}

        for file_path in image_files:
            rec = self.inspect_image_file(file_path)
            records.append(rec)
            sha_groups.setdefault(rec.sha256, []).append(rec)

        # Annotate duplicate clusters
        exact_duplicate_count = 0
        duplicate_clusters_count = 0

        for sha, group in sha_groups.items():
            if len(group) > 1:
                duplicate_clusters_count += 1
                for idx, rec in enumerate(group):
                    rec.is_exact_duplicate = True
                    rec.duplicate_cluster_id = sha[:16]
                    rec.duplicate_count = len(group)
                    rec.duplicate_index = idx
                    rec.is_canonical = (idx == 0)
                    if idx > 0:
                        exact_duplicate_count += 1

        total_bytes = sum(r.file_size_bytes for r in records)
        corrupt_count = sum(1 for r in records if r.is_corrupt)
        unique_hashes = len(sha_groups)

        # Size bands distribution
        size_bands = {
            "micro_under_5kb": sum(1 for r in records if r.file_size_bytes < 5_000),
            "small_5kb_to_20kb": sum(1 for r in records if 5_000 <= r.file_size_bytes < 20_000),
            "medium_20kb_to_100kb": sum(1 for r in records if 20_000 <= r.file_size_bytes < 100_000),
            "large_100kb_to_500kb": sum(1 for r in records if 100_000 <= r.file_size_bytes < 500_000),
            "xlarge_500kb_to_1mb": sum(1 for r in records if 500_000 <= r.file_size_bytes < 1_000_000),
            "high_res_over_1mb": sum(1 for r in records if r.file_size_bytes >= 1_000_000),
        }

        summary = {
            "inventory_run_id": f"inv-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_files_scanned": len(records),
            "total_bytes": total_bytes,
            "total_megabytes": round(total_bytes / (1024 * 1024), 2),
            "unique_binary_hashes": unique_hashes,
            "exact_duplicates_count": exact_duplicate_count,
            "duplicate_clusters_count": duplicate_clusters_count,
            "corrupt_files_count": corrupt_count,
            "size_bands": size_bands,
        }

        logger.info(
            f"✅ Inventory complete: {len(records):,} files scanned ({summary['total_megabytes']} MB) | "
            f"{unique_hashes:,} unique binaries | {exact_duplicate_count:,} duplicate occurrences."
        )

        return records, summary
