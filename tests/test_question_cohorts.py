"""
tests/test_question_cohorts.py

Unit & Integration Tests for Question Cohort Tagging (OLD_MCQ vs NEW_MCQ) and Filters.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    Question,
    QuestionStatus,
    QuestionType,
    User,
    UserRole,
)
from backend.api.main import app
from backend.api.routes.questions import get_db
from backend.api.routes.auth import get_current_user


@pytest.fixture
def cohort_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()

    # Create admin
    admin = User(
        id="user-admin-cohort",
        email="admin@medical-exam.ai",
        name="Admin User",
        role=UserRole.ADMIN,
        is_email_verified=True,
    )
    session.add(admin)
    session.flush()

    # Question 1: OLD_MCQ (MedMCQA Legacy)
    q1 = Question(
        id="q-old-1",
        external_source="medmcqa",
        external_source_id="medmcqa-12345",
        speciality="Pathology",
        subject="General Pathology",
        stem="Which cellular organelle is responsible for oxidative phosphorylation?",
        options=[{"id": "A", "text": "Mitochondria"}, {"id": "B", "text": "Ribosome"}],
        correct_option="A",
        correct_index=0,
        is_labeled=True,
        status=QuestionStatus.IMPORTED,
        origin_cohort="OLD_MCQ",
        tags=["OLD_MCQ", "LEGACY_MEDMCQA"],
        has_images=False,
        image_assets=[],
        content_hash="h1",
        exact_stem_hash="esh1",
        norm_stem_hash="nsh1",
    )

    # Question 2: NEW_MCQ (Robbins Evidence-Grounded)
    q2 = Question(
        id="q-new-1",
        external_source="AI_GENERATED",
        external_source_id="ai-gen-8888",
        speciality="Pathology",
        subject="Pathology",
        stem="Regarding HER2 IHC testing criteria, what score indicates strong circumferential staining?",
        options=[{"id": "A", "text": "3+"}, {"id": "B", "text": "1+"}],
        correct_option="A",
        correct_index=0,
        is_labeled=True,
        status=QuestionStatus.GENERATED,
        origin_cohort="NEW_MCQ",
        tags=["NEW_MCQ", "EVIDENCE_GROUNDED", "ROBBINS_11E"],
        has_images=False,
        image_assets=[],
        content_hash="h2",
        exact_stem_hash="esh2",
        norm_stem_hash="nsh2",
    )

    # Question 3: MULTIMODAL_IMAGE_MCQ
    q3 = Question(
        id="q-mm-1",
        external_source="MULTIMODAL_AI",
        external_source_id="mm-gen-9999",
        speciality="Pathology",
        subject="Surgical Pathology",
        stem="The biopsy specimen below shows classical owl-eye cells. What is the diagnosis?",
        options=[{"id": "A", "text": "Hodgkin Lymphoma"}, {"id": "B", "text": "Burkitt Lymphoma"}],
        correct_option="A",
        correct_index=0,
        is_labeled=True,
        status=QuestionStatus.GENERATED,
        origin_cohort="MULTIMODAL_IMAGE_MCQ",
        tags=["MULTIMODAL_IMAGE_MCQ", "HISTOLOGY_VIGNETTE"],
        has_images=True,
        image_assets=[{"image_id": "img-rs-cell"}],
        content_hash="h3",
        exact_stem_hash="esh3",
        norm_stem_hash="nsh3",
    )

    session.add_all([q1, q2, q3])
    session.commit()

    yield session
    session.close()


def test_question_cohort_filtering(cohort_test_db):
    admin_user = cohort_test_db.query(User).filter(User.email == "admin@medical-exam.ai").first()

    app.dependency_overrides[get_db] = lambda: cohort_test_db
    app.dependency_overrides[get_current_user] = lambda: admin_user

    client = TestClient(app)

    # 1. Filter cohort = OLD_MCQ
    resp_old = client.get("/api/questions?cohort=OLD_MCQ")
    assert resp_old.status_code == 200
    data_old = resp_old.json()
    assert len(data_old["items"]) == 1
    assert data_old["items"][0]["id"] == "q-old-1"
    assert data_old["items"][0]["origin_cohort"] == "OLD_MCQ"
    assert "LEGACY_MEDMCQA" in data_old["items"][0]["tags"]

    # 2. Filter cohort = NEW_MCQ
    resp_new = client.get("/api/questions?cohort=NEW_MCQ")
    assert resp_new.status_code == 200
    data_new = resp_new.json()
    assert len(data_new["items"]) == 1
    assert data_new["items"][0]["id"] == "q-new-1"
    assert data_new["items"][0]["origin_cohort"] == "NEW_MCQ"
    assert "ROBBINS_11E" in data_new["items"][0]["tags"]

    # 3. Filter has_images = True
    resp_img = client.get("/api/questions?has_images=true")
    assert resp_img.status_code == 200
    data_img = resp_img.json()
    assert len(data_img["items"]) == 1
    assert data_img["items"][0]["id"] == "q-mm-1"
    assert data_img["items"][0]["has_images"] is True

    app.dependency_overrides.clear()
