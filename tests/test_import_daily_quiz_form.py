"""
tests/test_import_daily_quiz_form.py

Unit tests for Google Form & Daily Quiz parsing and database ingestion pipeline.
"""

import pytest
from scripts.import_daily_quiz_form import extract_from_raw_text, compute_hashes, build_question_record


def test_extract_from_raw_text_standard():
    sample_text = """
    1. Which of the following features is characteristic of Papillary Urothelial Neoplasm of Low Malignant Potential (PUNLMP)?
    A. Marked nuclear pleomorphism and frequent mitotic figures
    B. Preserved urothelial polarity with delicate branching fibrovascular cores and minimal cytologic atypia
    C. Full thickness nuclear atypia with denudation
    D. True destructive stromal invasion into muscularis propria
    Answer: B
    Explanation: PUNLMP exhibits delicate papillae, preserved architectural polarity, and minimal cytologic atypia without stromal invasion.

    2. In the WHO 2022 / ICC classification, which immunohistochemical marker pattern best supports high-grade urothelial carcinoma over reactive urothelium?
    A. Diffuse strong full-thickness p53 positivity, CK20 positivity in all layers, and elevated Ki-67
    B. Basal-only CK20 and patchy wild-type p53
    C. Weak umbrella cell CK20 with basal p63
    D. Absence of GATA3 and CDX2 positivity
    Ans: A
    Discussion: High-grade urothelial carcinoma / CIS shows aberrant p53 (diffuse strong or complete null), diffuse full-thickness CK20 expression, and high Ki-67 index.
    """
    
    questions = extract_from_raw_text(
        sample_text,
        day_label="Day 077",
        topic_title="Urothelial tumours — Papilloma, PUNLMP, low-grade papillary urothelial carcinoma"
    )
    
    assert len(questions) == 2
    
    # Check Q1
    q1 = questions[0]
    assert "PUNLMP" in q1["stem"]
    assert len(q1["options"]) == 4
    assert q1["correct_option"] == "B"
    assert q1["correct_index"] == 1
    assert "PUNLMP exhibits delicate papillae" in q1["explanation"]
    
    # Check Q2
    q2 = questions[1]
    assert "WHO 2022" in q2["stem"]
    assert len(q2["options"]) == 4
    assert q2["correct_option"] == "A"
    assert q2["correct_index"] == 0
    assert "High-grade urothelial carcinoma" in q2["explanation"]


def test_compute_hashes_and_build_record():
    raw_q = {
        "question_number": 1,
        "stem": "Which marker is positive in urothelial differentiation?",
        "options": [
            {"key": "A", "text": "GATA3"},
            {"key": "B", "text": "TTF-1"},
            {"key": "C", "text": "HepPar-1"},
            {"key": "D", "text": "Synaptophysin"}
        ],
        "correct_option": "A",
        "correct_index": 0,
        "explanation": "GATA3 is a sensitive marker for urothelial and breast differentiation."
    }
    
    q_rec = build_question_record(
        raw_q=raw_q,
        day_id="Day 077",
        topic_title="Urothelial tumours",
        origin_url="https://forms.gle/VAztnRvN15MJnhuK6"
    )
    
    assert q_rec.external_source == "daily_pathology_quiz"
    assert q_rec.external_source_id == "daily_quiz_day_077_q1"
    assert q_rec.speciality == "Pathology"
    assert q_rec.primary_topic_id == "TOPIC-RENAL-PATH"
    assert q_rec.correct_option == "A"
    assert q_rec.correct_index == 0
    assert q_rec.is_labeled is True
    assert "DAILY_PATHOLOGY_QUIZ" in q_rec.origin_cohort
