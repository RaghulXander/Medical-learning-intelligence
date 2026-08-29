"""Curated first-level Pathology ontology and deterministic legacy-topic mapper."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class PathologyTopicDefinition:
    code: str
    name: str
    parent_code: str
    aliases: tuple[str, ...]


PATHOLOGY_TOPICS = (
    PathologyTopicDefinition("TOPIC-GEN-FOUNDATIONS", "General Pathology Foundations", "SUBJ-GEN-PATH", ("general pathology", "general concepts", "basic concepts", "cellular pathology")),
    PathologyTopicDefinition("TOPIC-CELL-INJURY", "Cell Injury, Death & Adaptation", "SUBJ-GEN-PATH", ("cell injury", "cell death", "necrosis", "apoptosis", "cellular adaptation")),
    PathologyTopicDefinition("TOPIC-INFLAMMATION", "Inflammation & Repair", "SUBJ-GEN-PATH", ("inflammation", "wound healing", "tissue repair", "granuloma")),
    PathologyTopicDefinition("TOPIC-HEMODYNAMIC", "Hemodynamic Disorders", "SUBJ-GEN-PATH", ("hemodynamic", "hemodynamics", "thrombosis", "embolism", "infarction", "shock", "edema")),
    PathologyTopicDefinition("TOPIC-IMMUNOPATH", "Immunopathology", "SUBJ-GEN-PATH", ("immunopathology", "immunity", "immunity disorder", "immunity disorders", "hypersensitivity", "autoimmune", "immunodeficiency", "transplant rejection")),
    PathologyTopicDefinition("TOPIC-GENETICS", "Genetic & Pediatric Diseases", "SUBJ-GEN-PATH", ("genetic", "genetics", "cytogenetic", "chromosomal", "pediatric", "paediatric", "congenital", "mendelian")),
    PathologyTopicDefinition("TOPIC-ENV-NUTRITION", "Environmental & Nutritional Pathology", "SUBJ-GEN-PATH", ("environmental pathology", "environment nutritional pathology", "environment and nutrition", "nutritional pathology")),
    PathologyTopicDefinition("TOPIC-INFECTIOUS", "Infectious Disease Pathology", "SUBJ-GEN-PATH", ("infectious disease", "infectious diseases", "microbial pathogenesis")),
    PathologyTopicDefinition("TOPIC-NEOPLASIA", "Neoplasia & Tumor Biology", "SUBJ-GEN-PATH", ("neoplasia", "tumor biology", "tumour biology", "oncogene", "tumor suppressor", "carcinogenesis")),
    PathologyTopicDefinition("TOPIC-HEM-FOUNDATIONS", "Hematology Foundations", "SUBJ-HEM-PATH", ("hematology", "haematology", "blood")),
    PathologyTopicDefinition("TOPIC-ANEMIAS", "Red Cell Disorders & Anemias", "SUBJ-HEM-PATH", ("anemia", "anemias", "anaemia", "anaemias", "r b c", "red cell", "erythrocyte", "hemolytic", "haemolytic", "hemoglobinopathy", "haemoglobinopathy")),
    PathologyTopicDefinition("TOPIC-LEUKEMIAS", "Myeloid Neoplasms & Leukemias", "SUBJ-HEM-PATH", ("leukemia", "leukaemia", "lukemia", "w b c", "myeloid", "myelodysplastic", "myeloproliferative")),
    PathologyTopicDefinition("TOPIC-LYMPHOMAS", "Lymphoid Neoplasms", "SUBJ-HEM-PATH", ("lymphoma", "hodgkin", "lymphoid neoplasm", "plasma cell", "myeloma")),
    PathologyTopicDefinition("TOPIC-HEMOSTASIS", "Hemostasis, Platelets & Coagulation", "SUBJ-HEM-PATH", ("hemostasis", "haemostasis", "platelet", "coagulation", "bleeding disorder", "bleeding disorders")),
    PathologyTopicDefinition("TOPIC-BLOOD-BANK", "Transfusion Medicine & Blood Banking", "SUBJ-HEM-PATH", ("transfusion", "blood bank", "blood banking", "crossmatch")),
    PathologyTopicDefinition("TOPIC-CARDIO-PATH", "Cardiovascular Pathology", "SUBJ-SYS-PATH", ("cardiovascular", "cardiac pathology", "heart disease", "blood vessel", "blood vessels", "vasculitis", "atherosclerosis")),
    PathologyTopicDefinition("TOPIC-LUNG-PATH", "Pulmonary & Thoracic Pathology", "SUBJ-SYS-PATH", ("lung", "pulmonary", "respiration", "respiratory system", "pleura", "thoracic")),
    PathologyTopicDefinition("TOPIC-RENAL-PATH", "Renal & Urinary Pathology", "SUBJ-SYS-PATH", ("renal", "kidney", "glomerular", "urinary tract", "urinary bladder", "urothelial")),
    PathologyTopicDefinition("TOPIC-GI-PATH", "Gastrointestinal & Hepatobiliary Pathology", "SUBJ-SYS-PATH", ("gastrointestinal", "g i t", "stomach", "gastric", "intestinal", "intestines", "colorectal", "liver", "hepatic", "pancreas", "gallbladder")),
    PathologyTopicDefinition("TOPIC-BREAST-PATH", "Breast Pathology", "SUBJ-SYS-PATH", ("breast", "mammary")),
    PathologyTopicDefinition("TOPIC-GYN-PATH", "Gynecologic Pathology", "SUBJ-SYS-PATH", ("gynecologic", "gynaecologic", "female genital tract", "cervix", "endometrium", "uterine", "ovarian", "ovary")),
    PathologyTopicDefinition("TOPIC-MALE-GU", "Male Genital Pathology", "SUBJ-SYS-PATH", ("male genital tract", "prostate", "testis", "testicular", "penile")),
    PathologyTopicDefinition("TOPIC-ENDOCRINE", "Endocrine Pathology", "SUBJ-SYS-PATH", ("endocrine", "endocrinology", "thyroid", "parathyroid", "adrenal", "pituitary", "diabetes")),
    PathologyTopicDefinition("TOPIC-SKIN-PATH", "Dermatopathology", "SUBJ-SYS-PATH", ("skin", "dermatopathology", "melanocytic")),
    PathologyTopicDefinition("TOPIC-BONE-SOFT", "Bone & Soft Tissue Pathology", "SUBJ-SYS-PATH", ("osteology", "bone tumor", "bone tumour", "soft tissue", "sarcoma")),
    PathologyTopicDefinition("TOPIC-CNS-PATH", "Neuropathology", "SUBJ-SYS-PATH", ("neuropathology", "nervous system", "central nervous system", "brain tumor", "brain tumour")),
    PathologyTopicDefinition("TOPIC-CYTOPATH", "Cytopathology", "SUBJ-MOL-PATH", ("cytopathology", "cytology", "pap smear", "fine needle aspiration", "fnac")),
    PathologyTopicDefinition("TOPIC-IHC-MOL", "Immunohistochemistry & Molecular Pathology", "SUBJ-MOL-PATH", ("immunohistochemistry", "ihc", "molecular pathology", "fish", "next generation sequencing")),
)

EXACT_ONLY_TOPIC_CODES = {"TOPIC-GEN-FOUNDATIONS", "TOPIC-HEM-FOUNDATIONS"}


@dataclass(frozen=True)
class TopicMatch:
    code: str
    confidence: float
    matched_aliases: tuple[str, ...]


def normalize_topic_text(value: Optional[str]) -> str:
    text = re.sub(r"[^\w]+", " ", value or "", flags=re.UNICODE)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def map_legacy_topic(values: Iterable[Optional[str]]) -> Optional[TopicMatch]:
    normalized_values = tuple(dict.fromkeys(filter(None, (normalize_topic_text(value) for value in values))))
    text = " ".join(normalized_values)
    if not text:
        return None

    matches: list[tuple[PathologyTopicDefinition, tuple[str, ...], int]] = []
    for topic in PATHOLOGY_TOPICS:
        if topic.code in EXACT_ONLY_TOPIC_CODES:
            aliases = tuple(
                alias for alias in topic.aliases if normalize_topic_text(alias) in normalized_values
            )
        else:
            aliases = tuple(
                alias
                for alias in topic.aliases
                if re.search(rf"\b{re.escape(normalize_topic_text(alias))}\b", text)
            )
        if aliases:
            matches.append((topic, aliases, max(len(normalize_topic_text(alias)) for alias in aliases)))

    if not matches:
        return None
    matches.sort(key=lambda item: (item[2], len(item[1])), reverse=True)
    best = matches[0]
    if len(matches) > 1 and matches[1][2:] == best[2:]:
        return None
    confidence = min(0.99, 0.72 + 0.06 * len(best[1]) + min(best[2], 30) / 300)
    return TopicMatch(best[0].code, round(confidence, 2), best[1])
