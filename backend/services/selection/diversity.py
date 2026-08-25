"""
backend/services/selection/diversity.py

Diversity & Deduplication Control Layer for Milestone 6.
Prevents exact duplicate IDs, normalized stem hash collisions, and concept overload.
"""

from typing import List, Set
from backend.services.selection.models import CandidateQuestion


class DiversityController:
    """
    Guarantees question uniqueness and controls conceptual redundancy.
    """

    @classmethod
    def deduplicate(
        cls,
        ranked_candidates: List[CandidateQuestion],
        target_count: int,
        max_questions_per_node: int = 15,
    ) -> List[CandidateQuestion]:
        """
        Filters candidates to ensure:
        1. No exact question ID duplicates.
        2. No normalized stem hash collisions.
        3. Conceptual diversity (caps excessive clustering on identical topic/concept nodes).
        """
        selected: List[CandidateQuestion] = []
        seen_ids: Set[str] = set()
        seen_stem_hashes: Set[str] = set()
        node_counts: dict = {}

        # 1. Primary Pass: Strict deduplication & concept diversity
        for c in ranked_candidates:
            if len(selected) >= target_count:
                break

            qid = c.question.id
            stem_hash = c.question.norm_stem_hash or c.question.content_hash
            node_id = c.question.primary_topic_id or "UNASSIGNED"

            # Exact ID check
            if qid in seen_ids:
                continue

            # Near-duplicate stem hash check
            if stem_hash and stem_hash in seen_stem_hashes:
                continue

            # Concept overload check (only apply if pool has alternatives)
            if node_counts.get(node_id, 0) >= max_questions_per_node:
                continue

            seen_ids.add(qid)
            if stem_hash:
                seen_stem_hashes.add(stem_hash)
            node_counts[node_id] = node_counts.get(node_id, 0) + 1
            selected.append(c)

        # 2. Secondary Fallback Pass: If concept capping prevented reaching target_count, relax concept cap
        if len(selected) < target_count:
            for c in ranked_candidates:
                if len(selected) >= target_count:
                    break

                qid = c.question.id
                stem_hash = c.question.norm_stem_hash or c.question.content_hash

                if qid in seen_ids:
                    continue
                if stem_hash and stem_hash in seen_stem_hashes:
                    continue

                seen_ids.add(qid)
                if stem_hash:
                    seen_stem_hashes.add(stem_hash)
                selected.append(c)

        return selected
