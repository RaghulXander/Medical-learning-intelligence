from backend.curation.image_ranker import RankInput, allocate_shortlist, rank_image


def candidate(**overrides):
    values = dict(
        width=800, height=600, file_size_bytes=200_000, entropy=6.0, blank_score=0.0,
        aspect_ratio=4 / 3, is_exact_duplicate=False, triage_class="PATHOLOGY_MICROSCOPY",
        link_confidence=0.98, link_type="FIGURE_CITATION", has_exact_page_provenance=True,
        evidence_text="Immunohistochemistry shows CD20 positivity in this clinical case.",
    )
    values.update(overrides)
    return RankInput(**values)


def test_high_quality_exactly_linked_image_ranks_above_fragment():
    useful = rank_image(candidate())
    fragment = rank_image(candidate(
        width=12, height=8, file_size_bytes=300, entropy=0.4, blank_score=0.95,
        aspect_ratio=12 / 8, has_exact_page_provenance=False, link_confidence=0,
        link_type="PAGE_CO_OCCURRENCE", evidence_text="",
    ))
    assert useful.score > fragment.score
    assert useful.suggested_utility_class == "IHC_OR_SPECIAL_STAIN"
    assert useful.requires_human_verification is True


def test_shortlist_never_reuses_an_asset():
    rows = []
    for index in range(100):
        rows.append({
            "image_asset_id": f"asset-{index // 2}", "occurrence_id": f"occ-{index}",
            "priority_score": 100 - index / 10, "suggested_utility_class": "PATHOLOGY_MICROSCOPY",
            "suggested_tags": [], "source_short_name": f"source-{index % 3}",
        })
    shortlist = allocate_shortlist(rows, total=20)
    assert len({row["image_asset_id"] for row in shortlist}) == len(shortlist)
    assert len({row["source_short_name"] for row in shortlist}) == 3
