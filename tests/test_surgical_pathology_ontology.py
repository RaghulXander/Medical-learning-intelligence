import copy
import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.domain.surgical_pathology_ontology import (
    OntologyMappingMethod,
    OntologyMappingRole,
    OntologyNodeType,
    OntologySchemeStatus,
    OntologySeedValidationError,
    load_surgical_pathology_seed,
    validate_ontology_seed,
)
from database.models import (
    Base,
    OntologyAlias,
    OntologyNode,
    OntologyScheme,
    Question,
    QuestionOntologyMapping,
    QuestionStatus,
    VerificationStatus,
)
from scripts.seed_surgical_pathology_ontology import seed_surgical_pathology_ontology


class TestSurgicalPathologyOntology(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)

    def test_seed_is_structurally_valid_and_versioned_as_draft(self):
        seed = load_surgical_pathology_seed()
        self.assertEqual(seed["scheme"]["version"], "2026.08-draft.1")
        self.assertEqual(seed["scheme"]["status"], "DRAFT")
        self.assertEqual(len(seed["nodes"]), 84)
        self.assertIn("online beta", seed["scheme"]["source_scope"][1]["edition"])
        alias_states = {
            alias["verification_status"]
            for node in seed["nodes"]
            for alias in node.get("aliases", [])
        }
        self.assertEqual(alias_states, {"AI_SUGGESTED"})

    def test_seed_contains_core_hierarchy_and_limited_breast_slice(self):
        seed = load_surgical_pathology_seed()
        by_code = {node["code"]: node for node in seed["nodes"]}
        self.assertEqual(by_code["SP"]["node_type"], OntologyNodeType.DISCIPLINE.value)
        self.assertEqual(by_code["SP-BREAST"]["parent_code"], "SP")
        self.assertEqual(
            by_code["SP-BREAST-IBC-NST"]["node_type"],
            OntologyNodeType.DIAGNOSTIC_ENTITY.value,
        )
        self.assertEqual(by_code["SP-BREAST-IBC-NST"]["parent_code"], "SP-BREAST-INVASIVE")

    def test_validation_rejects_parent_cycles(self):
        seed = copy.deepcopy(load_surgical_pathology_seed())
        by_code = {node["code"]: node for node in seed["nodes"]}
        by_code["SP-PRINCIPLES"]["parent_code"] = "SP-ANCILLARY"
        by_code["SP-ANCILLARY"]["parent_code"] = "SP-PRINCIPLES"
        with self.assertRaisesRegex(OntologySeedValidationError, "parent cycle"):
            validate_ontology_seed(seed)

    def test_validation_rejects_invalid_parent_type(self):
        seed = copy.deepcopy(load_surgical_pathology_seed())
        by_code = {node["code"]: node for node in seed["nodes"]}
        by_code["SP-BREAST-IBC-NST"]["parent_code"] = "SP-ANCILLARY-IHC"
        with self.assertRaisesRegex(OntologySeedValidationError, "cannot be below METHOD"):
            validate_ontology_seed(seed)

    def test_database_seed_is_idempotent_and_preserves_parentage(self):
        first = seed_surgical_pathology_ontology(self.engine)
        second = seed_surgical_pathology_ontology(self.engine)
        self.assertEqual(first["nodes_created"], 84)
        self.assertEqual(second["nodes_created"], 0)
        self.assertEqual(second["aliases_created"], 0)

        with self.Session() as session:
            self.assertEqual(session.query(OntologyScheme).count(), 1)
            self.assertEqual(session.query(OntologyNode).count(), 84)
            self.assertEqual(session.query(OntologyAlias).count(), 16)
            breast = session.query(OntologyNode).filter_by(code="SP-BREAST").one()
            epithelial = session.query(OntologyNode).filter_by(code="SP-BREAST-EPITHELIAL").one()
            invasive = session.query(OntologyNode).filter_by(code="SP-BREAST-INVASIVE").one()
            entity = session.query(OntologyNode).filter_by(code="SP-BREAST-IBC-NST").one()
            self.assertEqual(epithelial.parent_id, breast.id)
            self.assertEqual(invasive.parent_id, epithelial.id)
            self.assertEqual(entity.parent_id, invasive.id)

    def test_released_seed_version_cannot_be_changed(self):
        seed_surgical_pathology_ontology(self.engine)
        with self.Session() as session:
            scheme = session.query(OntologyScheme).one()
            scheme.status = OntologySchemeStatus.RELEASED
            session.commit()

        changed_seed = copy.deepcopy(load_surgical_pathology_seed())
        changed_seed["scheme"]["description"] = "Changed after release"
        with tempfile.TemporaryDirectory() as temp_dir:
            changed_path = Path(temp_dir) / "changed.json"
            changed_path.write_text(json.dumps(changed_seed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "released and immutable"):
                seed_surgical_pathology_ontology(self.engine, changed_path)

    def test_verified_mapping_does_not_change_question_approval_status(self):
        seed_surgical_pathology_ontology(self.engine)
        with self.Session() as session:
            breast = session.query(OntologyNode).filter_by(code="SP-BREAST").one()
            question = Question(
                id="m14-question",
                external_source="manual",
                external_source_id="manual-m14-question",
                stem="A sample educational question",
                options=[{"key": "A", "text": "Option A"}, {"key": "B", "text": "Option B"}],
                correct_option="A",
                correct_index=0,
                content_hash="m14-content-hash",
                exact_stem_hash="m14-exact-hash",
                norm_stem_hash="m14-normalized-hash",
                status=QuestionStatus.IMPORTED,
            )
            session.add(question)
            session.flush()
            session.add(
                QuestionOntologyMapping(
                    question_id=question.id,
                    node_id=breast.id,
                    mapping_role=OntologyMappingRole.PRIMARY,
                    mapping_method=OntologyMappingMethod.HUMAN,
                    verification_status=VerificationStatus.HUMAN_VERIFIED,
                    ontology_version="2026.08-draft.1",
                    mapped_by="test-reviewer",
                )
            )
            session.commit()
            session.refresh(question)
            self.assertEqual(question.status, QuestionStatus.IMPORTED)
            self.assertEqual(len(question.ontology_mappings), 1)


if __name__ == "__main__":
    unittest.main()
