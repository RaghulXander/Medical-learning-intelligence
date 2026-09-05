import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.question_editor_service import (
    EmptyQuestionEdit,
    QuestionEditConflict,
    edit_question,
)
from database.models import (
    Base,
    CognitiveLevel,
    DifficultyLevel,
    Question,
    QuestionRevision,
    QuestionStatus,
    QuestionType,
    User,
    UserRole,
)


class QuestionEditorServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.editor = User(email="editor@example.com", name="Editor", role=UserRole.REVIEWER)
        self.question = Question(
            external_source_id="editor-test-1",
            stem="Which option is the original correct answer?",
            options=[{"key": "A", "text": "Original"}, {"key": "B", "text": "Alternative"}],
            correct_option="A",
            correct_index=0,
            explanation="Original explanation",
            difficulty=DifficultyLevel.MEDIUM,
            cognitive_level=CognitiveLevel.RECALL,
            question_type=QuestionType.SINGLE_BEST_ANSWER,
            content_hash="a" * 64,
            exact_stem_hash="b" * 64,
            norm_stem_hash="c" * 64,
            status=QuestionStatus.HUMAN_REVIEW,
        )
        self.db.add_all([self.editor, self.question])
        self.db.commit()
        self.db.refresh(self.question)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def values(self, *, stem: str | None = None):
        return {
            "stem": stem or self.question.stem,
            "options": self.question.options,
            "correct_option": self.question.correct_option,
            "explanation": self.question.explanation,
            "difficulty": self.question.difficulty,
            "cognitive_level": self.question.cognitive_level,
            "question_type": self.question.question_type,
            "primary_topic_id": self.question.primary_topic_id,
            "learning_objective": self.question.learning_objective,
        }

    def test_edit_stores_previous_snapshot_and_updates_hashes(self):
        original_stem = self.question.stem
        revision = edit_question(
            self.db,
            self.question,
            editor_id=self.editor.id,
            expected_updated_at=self.question.updated_at,
            values=self.values(stem="Which option is the revised and correct answer?"),
            edit_notes="Clarified wording",
        )
        self.db.commit()
        stored = self.db.query(QuestionRevision).filter_by(id=revision.id).one()
        self.assertEqual(stored.revision_number, 1)
        self.assertEqual(stored.snapshot["stem"], original_stem)
        self.assertEqual(stored.changed_fields, ["stem"])
        self.assertNotEqual(self.question.content_hash, "a" * 64)

    def test_stale_edit_is_rejected(self):
        with self.assertRaises(QuestionEditConflict):
            edit_question(
                self.db,
                self.question,
                editor_id=self.editor.id,
                expected_updated_at=datetime.now(timezone.utc) - timedelta(days=1),
                values=self.values(stem="A stale editor tries to update this question."),
            )

    def test_identical_edit_is_rejected(self):
        with self.assertRaises(EmptyQuestionEdit):
            edit_question(
                self.db,
                self.question,
                editor_id=self.editor.id,
                expected_updated_at=self.question.updated_at,
                values=self.values(),
            )

    def test_edit_handles_options_with_id_or_dict_and_enum_values(self):
        # Set question with options containing 'id' instead of 'key'
        self.question.options = [{"id": "A", "text": "Choice A"}, {"id": "B", "text": "Choice B"}]
        self.db.commit()

        new_values = self.values(stem="Updated question with options format")
        new_values["options"] = [{"key": "A", "text": "Choice A Updated"}, {"key": "B", "text": "Choice B Updated"}]
        new_values["correct_option"] = "B"

        revision = edit_question(
            self.db,
            self.question,
            editor_id=self.editor.id,
            expected_updated_at=self.question.updated_at,
            values=new_values,
            edit_notes="Updated options format",
        )
        self.db.commit()
        self.assertEqual(revision.revision_number, 1)
        self.assertEqual(self.question.correct_index, 1)
        self.assertEqual(self.question.correct_option, "B")


if __name__ == "__main__":
    unittest.main()
