"""
tests/test_multimodal_engine.py

Unit & Integration Tests for Multimodal Pathology Image Engine & REST Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base, Question, User, UserRole
from backend.services.multimodal.models import (
    MagnificationLevel,
    MultimodalQuestionBlueprint,
    PathologyImageAsset,
    StainType,
)
from backend.services.multimodal.image_catalog import PathologyImageCatalog, get_image_catalog
from backend.services.multimodal.generator import MultimodalMCQGenerator
from backend.api.main import app
from backend.api.routes.multimodal import get_db
from backend.api.routes.auth import get_current_user


@pytest.fixture
def mm_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()

    editor = User(
        id="user-editor-mm",
        email="editor-mm@medical-exam.ai",
        name="Multimodal Editor",
        role=UserRole.ADMIN,
        is_email_verified=True,
    )
    session.add(editor)
    session.commit()

    yield session
    session.close()


def test_image_catalog_queries():
    catalog = PathologyImageCatalog()

    # Query all
    all_imgs = catalog.list_images()
    assert len(all_imgs) >= 4

    # Query by stain
    her2_imgs = catalog.list_images(stain_type=StainType.IHC_HER2)
    assert len(her2_imgs) == 1
    assert "HER2" in her2_imgs[0].title

    # Query by organ
    renal_imgs = catalog.list_images(organ_system="Kidney")
    assert len(renal_imgs) == 1
    assert "Amyloidosis" in renal_imgs[0].diagnosis


def test_multimodal_mcq_generator():
    generator = MultimodalMCQGenerator()
    bp = MultimodalQuestionBlueprint(
        topic="Breast",
        learning_objective="Interpret HER2 IHC overexpression",
        target_image_id="img-breast-her2-3plus",
    )

    mcq = generator.generate_image_mcq(blueprint=bp)
    assert mcq.correct_option == "A"
    assert len(mcq.options) == 4
    assert mcq.metadata["has_images"] is True
    assert len(mcq.metadata["image_assets"]) == 1
    assert mcq.metadata["image_assets"][0]["image_id"] == "img-breast-her2-3plus"
    assert "IHC_HER2" in mcq.stem or "40X" in mcq.stem


def test_multimodal_api_endpoints(mm_test_db):
    editor = mm_test_db.query(User).filter(User.email == "editor-mm@medical-exam.ai").first()

    app.dependency_overrides[get_db] = lambda: mm_test_db
    app.dependency_overrides[get_current_user] = lambda: editor

    client = TestClient(app)

    # 1. GET /api/multimodal/images
    img_resp = client.get("/api/multimodal/images")
    assert img_resp.status_code == 200
    img_data = img_resp.json()
    assert img_data["total"] >= 4

    # 2. GET /api/multimodal/images/{image_id}
    detail_resp = client.get("/api/multimodal/images/img-hodgkin-reed-sternberg")
    assert detail_resp.status_code == 200
    assert "Reed-Sternberg" in detail_resp.json()["title"]

    # 3. POST /api/multimodal/generate
    gen_payload = {
        "image_id": "img-breast-her2-3plus",
        "topic": "Breast Pathology",
        "learning_objective": "HER2 3+ IHC score interpretation",
        "difficulty": "HARD",
        "cognitive_level": "APPLICATION",
        "target_exam": "NEET_SS",
    }
    gen_resp = client.post("/api/multimodal/generate", json=gen_payload)
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["status"] == "success"
    assert gen_data["has_images"] is True
    assert len(gen_data["image_assets"]) == 1
    assert gen_data["origin_cohort"] == "MULTIMODAL_IMAGE_MCQ"

    app.dependency_overrides.clear()
