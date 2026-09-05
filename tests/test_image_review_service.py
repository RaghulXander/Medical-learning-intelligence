import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.image_review_service import ImageReviewConflictError, ImageReviewService
from database.models import (
    Base,
    DocumentChunk,
    ImageAsset,
    ImageOccurrence,
    ImageReview,
    ImageTextEvidenceLink,
    Source,
    SourceDocument,
    User,
    UserRole,
)


class TestImageReviewService(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.reviewer = User(email="image-admin@example.com", name="Image Admin", role=UserRole.ADMIN)
        source = Source(short_name="robbins_review", title="Robbins Review")
        document = SourceDocument(source=source, title="Review document", edition="11")
        self.chunk = DocumentChunk(
            document=document,
            chunk_index=1,
            pdf_page=42,
            textbook_page=30,
            content="The figure shows diagnostic morphology with the stated immunostain pattern.",
            content_hash="c" * 64,
            word_count=10,
        )
        self.asset = ImageAsset(
            sha256="a" * 64,
            pixel_hash="b" * 64,
            filename="figure.png",
            storage_uri="https://private.example/pathology/figure.png",
            width=800,
            height=600,
            aspect_ratio=4 / 3,
            file_size_bytes=100_000,
            format="PNG",
            triage_class="PATHOLOGY_MICROSCOPY",
            curation_status="CURATED_VALID",
            rights_status="RESTRICTED_INTERNAL",
            storage_access_status="PRIVATE_VERIFIED",
        )
        self.occurrence = ImageOccurrence(
            image_asset=self.asset,
            source_document=document,
            pdf_page=42,
            textbook_page=30,
            figure_label="Fig. 2",
        )
        self.link = ImageTextEvidenceLink(
            image_asset=self.asset,
            chunk=self.chunk,
            verification_status="AI_SUGGESTED",
            confidence=0.8,
        )
        self.db.add_all([self.reviewer, self.occurrence, self.link])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_question_approval_binds_exact_occurrence_and_opens_eligibility(self):
        result = ImageReviewService.save(
            self.db,
            self.asset.id,
            reviewer_id=self.reviewer.id,
            expected_revision=1,
            utility_class="IHC_OR_SPECIAL_STAIN",
            diagnosis="Example verified diagnosis",
            stain="IHC marker",
            magnification="20X",
            caption="Reviewed figure context supporting the diagnosis.",
            occurrence_id=self.occurrence.id,
            link_id=self.link.id,
            notes="Image and complete same-page passage inspected.",
            action="APPROVE_INTERNAL_QUESTION_CANDIDATE",
        )
        self.assertEqual(result["curation_status"], "APPROVED_INTERNAL_QUESTION_CANDIDATE")
        self.assertEqual(result["metadata_verification_status"], "HUMAN_VERIFIED")
        self.assertEqual(result["links"][0]["occurrence_id"], self.occurrence.id)
        self.assertEqual(result["links"][0]["verification_status"], "HUMAN_VERIFIED")
        self.assertEqual(ImageReviewService.summary(self.db)["eligible_question_assets"], 1)
        self.assertEqual(self.db.query(ImageReview).count(), 1)

        page = ImageReviewService.list_assets(self.db, source="robbins_review")
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["source_short_name"], "robbins_review")
        self.assertEqual(page["items"][0]["pdf_page"], 42)
        self.assertEqual(page["items"][0]["verified_link_count"], 1)

    def test_mismatched_occurrence_page_fails_closed(self):
        other = ImageOccurrence(
            image_asset=self.asset,
            source_document_id=self.occurrence.source_document_id,
            pdf_page=43,
        )
        self.db.add(other)
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "same.*PDF page|match"):
            ImageReviewService.save(
                self.db,
                self.asset.id,
                reviewer_id=self.reviewer.id,
                expected_revision=1,
                utility_class="PATHOLOGY_MICROSCOPY",
                diagnosis="Diagnosis",
                stain=None,
                magnification=None,
                caption="Caption",
                occurrence_id=other.id,
                link_id=self.link.id,
                notes="Mismatch should be rejected.",
                action="APPROVE_INTERNAL_QUESTION_CANDIDATE",
            )

    def test_stale_revision_is_rejected(self):
        self.asset.review_revision = 2
        self.db.commit()
        with self.assertRaises(ImageReviewConflictError):
            ImageReviewService.save(
                self.db,
                self.asset.id,
                reviewer_id=self.reviewer.id,
                expected_revision=1,
                utility_class="PATHOLOGY_MICROSCOPY",
                diagnosis=None,
                stain=None,
                magnification=None,
                caption=None,
                occurrence_id=None,
                link_id=None,
                notes="Stale update.",
            )


if __name__ == "__main__":
    unittest.main()
