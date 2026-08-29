import unittest

from backend.domain.pathology_ontology import map_legacy_topic, normalize_topic_text


class TestPathologyOntology(unittest.TestCase):
    def test_normalizes_source_topic_without_destroying_original(self):
        self.assertEqual(normalize_topic_text("Gynaecologic—Pathology"), "gynaecologic pathology")

    def test_maps_common_legacy_topics(self):
        self.assertEqual(map_legacy_topic(("Breast carcinoma",)).code, "TOPIC-BREAST-PATH")
        self.assertEqual(map_legacy_topic(("Hodgkin lymphoma",)).code, "TOPIC-LYMPHOMAS")
        self.assertEqual(map_legacy_topic(("Renal pathology",)).code, "TOPIC-RENAL-PATH")

    def test_does_not_guess_unknown_topic(self):
        self.assertIsNone(map_legacy_topic(("miscellaneous facts",)))

    def test_prefers_more_specific_alias(self):
        match = map_legacy_topic(("Molecular pathology of breast carcinoma",))
        self.assertEqual(match.code, "TOPIC-IHC-MOL")

    def test_broad_foundation_alias_does_not_override_specific_topic(self):
        match = map_legacy_topic(("Basic Concepts and Vascular changes of Acute Inflammation",))
        self.assertEqual(match.code, "TOPIC-INFLAMMATION")


if __name__ == "__main__":
    unittest.main()
