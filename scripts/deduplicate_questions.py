"""
scripts/deduplicate_questions.py

Analyzes duplicates and similarity signals across questions without dropping any records.
Annotates duplicate clusters and logs metrics so that 100% of original records are preserved.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def analyze_and_annotate_duplicates(
    records: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Analyzes exact and normalized duplicate signals across normalized question records.
    Attaches duplicate cluster metadata to any records that share content or stem hashes.
    Preserves all records without dropping any.
    """
    content_hash_map: Dict[str, List[int]] = defaultdict(list)
    norm_stem_hash_map: Dict[str, List[int]] = defaultdict(list)
    id_map: Dict[str, List[int]] = defaultdict(list)

    for idx, rec in enumerate(records):
        id_val = rec.get("id")
        content_hash = rec.get("content_hash")
        norm_stem_hash = rec.get("norm_stem_hash")

        if id_val:
            id_map[id_val].append(idx)
        if content_hash:
            content_hash_map[content_hash].append(idx)
        if norm_stem_hash:
            norm_stem_hash_map[norm_stem_hash].append(idx)

    # Detect duplicate clusters
    duplicate_content_clusters = {h: idxs for h, idxs in content_hash_map.items() if len(idxs) > 1}
    duplicate_stem_clusters = {h: idxs for h, idxs in norm_stem_hash_map.items() if len(idxs) > 1}
    duplicate_ids = {i: idxs for i, idxs in id_map.items() if len(idxs) > 1}

    # Annotate records with duplicate cluster signals
    for content_hash, idxs in duplicate_content_clusters.items():
        cluster_id = f"cluster-content-{content_hash[:12]}"
        for idx in idxs:
            if "duplicate_signals" not in records[idx]:
                records[idx]["duplicate_signals"] = {}
            records[idx]["duplicate_signals"]["content_duplicate_cluster"] = cluster_id
            records[idx]["duplicate_signals"]["content_duplicate_count"] = len(idxs)

    for stem_hash, idxs in duplicate_stem_clusters.items():
        cluster_id = f"cluster-stem-{stem_hash[:12]}"
        for idx in idxs:
            if "duplicate_signals" not in records[idx]:
                records[idx]["duplicate_signals"] = {}
            records[idx]["duplicate_signals"]["stem_duplicate_cluster"] = cluster_id
            records[idx]["duplicate_signals"]["stem_duplicate_count"] = len(idxs)

    report = {
        "total_records_processed": len(records),
        "unique_ids": len(id_map),
        "duplicate_id_count": len(duplicate_ids),
        "unique_content_hashes": len(content_hash_map),
        "duplicate_content_clusters_count": len(duplicate_content_clusters),
        "records_in_duplicate_content_clusters": sum(len(idxs) for idxs in duplicate_content_clusters.values()),
        "unique_norm_stem_hashes": len(norm_stem_hash_map),
        "duplicate_stem_clusters_count": len(duplicate_stem_clusters),
        "records_in_duplicate_stem_clusters": sum(len(idxs) for idxs in duplicate_stem_clusters.values()),
    }

    logger.info(
        f"Deduplication Analysis: {report['total_records_processed']} records, "
        f"{report['unique_content_hashes']} unique content hashes, "
        f"{report['duplicate_content_clusters_count']} duplicate clusters found. "
        f"100% of records preserved."
    )

    return records, report
