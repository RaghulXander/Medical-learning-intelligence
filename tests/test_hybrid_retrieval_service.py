from backend.services.embedding_service import DeterministicMockEmbeddingProvider
from backend.services.hybrid_retrieval_service import (
    HybridRetrievalConfig,
    HybridRetrievalService,
)


def test_configuration_hash_is_stable_and_changes_with_config():
    base = HybridRetrievalConfig()
    same = HybridRetrievalConfig()
    changed = HybridRetrievalConfig(dense_weight=0.7, lexical_weight=0.3)

    assert base.configuration_hash == same.configuration_hash
    assert base.configuration_hash != changed.configuration_hash


def test_weighted_rrf_is_deterministic_and_rewards_agreement():
    service = HybridRetrievalService(
        embedding_provider=DeterministicMockEmbeddingProvider(),
        config=HybridRetrievalConfig(dense_weight=0.65, lexical_weight=0.35),
    )
    fused = service._fuse(
        dense=[("dense-only", 0.91), ("both", 0.82)],
        lexical=[("both", 0.75), ("lexical-only", 0.5)],
    )

    assert [item[0] for item in fused] == ["both", "dense-only", "lexical-only"]
    assert dict((item[0], item[2]) for item in fused)["dense-only"] == 0.91
    assert dict((item[0], item[3]) for item in fused)["lexical-only"] == 0.5
