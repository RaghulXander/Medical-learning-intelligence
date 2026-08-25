"""
scripts/seed_curriculum.py

Seeds comprehensive Courses, Users, Canonical Knowledge Domain Curriculum,
Cross-Course Topic Mappings (with depth levels), and Source Documents / Chunks.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_engine, init_db, session_scope
from database.models import (
    Course,
    CourseCurriculumMapping,
    CurriculumLevel,
    CurriculumTopic,
    DepthLevel,
    DocumentChunk,
    Source,
    SourceDocument,
    SourceType,
    User,
    UserRole,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Foundational Pathology Knowledge Sources
FOUNDATIONAL_SOURCES = [
    {
        "short_name": "robbins_pathology",
        "title": "Robbins & Cotran Pathologic Basis of Disease",
        "author": "Kumar, Abbas, Aster",
        "edition": "10th Edition",
        "year": 2020,
        "publisher": "Elsevier",
        "source_type": SourceType.TEXTBOOK,
    },
    {
        "short_name": "who_blue_books",
        "title": "WHO Classification of Tumours (Blue Books)",
        "author": "World Health Organization / IARC",
        "edition": "5th Edition",
        "year": 2022,
        "publisher": "IARC Press",
        "source_type": SourceType.WHO_CLASSIFICATION,
    },
    {
        "short_name": "sternberg_surgical_pathology",
        "title": "Sternberg's Diagnostic Surgical Pathology",
        "author": "Mills, Greenson, Hornick, Longacre",
        "edition": "7th Edition",
        "year": 2021,
        "publisher": "Wolters Kluwer",
        "source_type": SourceType.TEXTBOOK,
    },
    {
        "short_name": "ackerman_surgical_pathology",
        "title": "Rosai and Ackerman's Surgical Pathology",
        "author": "Goldblum, Lamps, McKenney, Myers",
        "edition": "11th Edition",
        "year": 2017,
        "publisher": "Elsevier",
        "source_type": SourceType.TEXTBOOK,
    },
    {
        "short_name": "diagnostic_ihc",
        "title": "Diagnostic Immunohistochemistry: Theranostic and Genomic Applications",
        "author": "Dabbs",
        "edition": "6th Edition",
        "year": 2021,
        "publisher": "Elsevier",
        "source_type": SourceType.TEXTBOOK,
    },
    {
        "short_name": "koss_cytology",
        "title": "Koss' Diagnostic Cytology and Its Histopathologic Bases",
        "author": "Koss, Melamed",
        "edition": "5th Edition",
        "year": 2005,
        "publisher": "Lippincott Williams & Wilkins",
        "source_type": SourceType.TEXTBOOK,
    },
]

INITIAL_USERS = [
    {
        "email": "raghuldpi95@gmail.com",
        "name": "Dr. Raghul Xander (Super Admin)",
        "role": UserRole.SUPER_ADMIN,
    },
    {
        "email": "raghuljayan@gmail.com",
        "name": "Dr. Raghul Jayan (Super Admin)",
        "role": UserRole.SUPER_ADMIN,
    },
    {
        "email": "admin@medicalexam.ai",
        "name": "Dr. Chief Pathologist (Admin)",
        "role": UserRole.ADMIN,
    },
    {
        "email": "reviewer@medicalexam.ai",
        "name": "Dr. Editorial Reviewer",
        "role": UserRole.REVIEWER,
    },
    {
        "email": "student@medicalexam.ai",
        "name": "Pathology Resident",
        "role": UserRole.USER,
    },
]

INITIAL_COURSES = [
    {
        "code": "DM-ONCOPATH",
        "name": "DM / DrNB Oncopathology",
        "target_audience": "Super-Specialty",
        "description": "Advanced oncopathology curriculum covering tumor immunohistochemistry, molecular diagnostics, hematopathology, and WHO classifications.",
    },
    {
        "code": "MD-PATH",
        "name": "MD / DNB Pathology",
        "target_audience": "Postgraduate",
        "description": "Comprehensive residency curriculum in general pathology, systemic pathology, hematology, and cytopathology.",
    },
    {
        "code": "NEET-PG",
        "name": "NEET-PG / INI-CET Pathology",
        "target_audience": "Postgraduate Entrance",
        "description": "High-yield pathology topics for medical PG entrance exams.",
    },
    {
        "code": "MBBS-PATH",
        "name": "MBBS 2nd Professional Pathology",
        "target_audience": "Undergraduate",
        "description": "Undergraduate CBME/NMC aligned medical curriculum in pathology.",
    },
]

# Canonical Knowledge Domain Tree (Independent of any single exam or course)
CURRICULUM_TREE = [
    # 1. Root Speciality
    ("SPEC-PATH", "Pathology", CurriculumLevel.SPECIALITY, None, "Broad specialty of disease pathology", {}),

    # 2. Subjects under Pathology
    ("SUBJ-GEN-PATH", "General Pathology", CurriculumLevel.SUBJECT, "SPEC-PATH", "Cellular reactions, inflammation, genetics, and neoplasia", {}),
    ("SUBJ-HEM-PATH", "Hematopathology", CurriculumLevel.SUBJECT, "SPEC-PATH", "Disorders of erythrocytes, leukocytes, platelets, and lymph nodes", {}),
    ("SUBJ-SYS-PATH", "Systemic & Surgical Pathology", CurriculumLevel.SUBJECT, "SPEC-PATH", "Organ system pathology and surgical specimen diagnostics", {}),
    ("SUBJ-MOL-PATH", "Molecular & Diagnostic IHC", CurriculumLevel.SUBJECT, "SPEC-PATH", "Immunohistochemical markers, molecular diagnostics, and genomic assays", {}),

    # 3. Topics under General Pathology
    ("TOPIC-CELL-INJURY", "Cell Injury, Cell Death & Adaptations", CurriculumLevel.TOPIC, "SUBJ-GEN-PATH", "Mechanisms of cellular injury, adaptation, and pathways of cell death", {}),
    ("TOPIC-INFLAMMATION", "Inflammation & Tissue Repair", CurriculumLevel.TOPIC, "SUBJ-GEN-PATH", "Acute vs chronic inflammation, chemical mediators, and wound healing", {}),
    ("TOPIC-NEOPLASIA", "Neoplasia & Tumor Biology", CurriculumLevel.TOPIC, "SUBJ-GEN-PATH", "Hallmarks of cancer, oncogenes, tumor suppressors, and metastasis", {}),
    ("TOPIC-GENETICS", "Genetic & Pediatric Diseases", CurriculumLevel.TOPIC, "SUBJ-GEN-PATH", "Mendelian disorders, cytogenetic abnormalities, and pediatric tumors", {}),

    # 4. Subtopics under Cell Injury
    ("SUBTOPIC-APOPTOSIS", "Apoptosis & Programmed Cell Death", CurriculumLevel.SUBTOPIC, "TOPIC-CELL-INJURY", "Intrinsic (mitochondrial) and extrinsic (death receptor) apoptotic pathways", {}),
    ("SUBTOPIC-NECROSIS", "Patterns of Tissue Necrosis", CurriculumLevel.SUBTOPIC, "TOPIC-CELL-INJURY", "Coagulative, liquefactive, caseous, fat, and gangrenous necrosis", {}),
    ("SUBTOPIC-CELL-ADAPT", "Cellular Adaptations", CurriculumLevel.SUBTOPIC, "TOPIC-CELL-INJURY", "Hypertrophy, hyperplasia, atrophy, and metaplasia", {}),

    # 5. Subtopics under Neoplasia
    ("SUBTOPIC-TUMOR-SUPPRESSORS", "Tumor Suppressor Genes & Oncogenes", CurriculumLevel.SUBTOPIC, "TOPIC-NEOPLASIA", "TP53, RB1, BRCA1/2, APC, KRAS, and EGFR pathways", {}),
    ("SUBTOPIC-METASTASIS", "Invasion & Metastasis Cascades", CurriculumLevel.SUBTOPIC, "TOPIC-NEOPLASIA", "E-cadherin loss, basement membrane degradation, and vascular dissemination", {}),

    # 6. Topics under Hematopathology
    ("TOPIC-ANEMIAS", "Red Blood Cell Disorders & Anemias", CurriculumLevel.TOPIC, "SUBJ-HEM-PATH", "Microcytic, macrocytic, normocytic, and hemolytic anemias", {}),
    ("TOPIC-LYMPHOMAS", "WHO Classification of Lymphomas", CurriculumLevel.TOPIC, "SUBJ-HEM-PATH", "Hodgkin lymphoma, Non-Hodgkin B-cell and T-cell neoplasms", {}),
    ("TOPIC-LEUKEMIAS", "Acute & Chronic Leukemias", CurriculumLevel.TOPIC, "SUBJ-HEM-PATH", "AML, ALL, CML, and Myelodysplastic syndromes", {}),

    # 7. Topics & Subtopics under Systemic Pathology
    ("TOPIC-BREAST-PATH", "Breast Pathology & Oncopathology", CurriculumLevel.TOPIC, "SUBJ-SYS-PATH", "Benign lesions, in-situ carcinomas, and invasive breast cancer", {}),
    ("SUBTOPIC-HER2-TESTING", "HER2/neu IHC & FISH Testing", CurriculumLevel.SUBTOPIC, "TOPIC-BREAST-PATH", "ASCO/CAP guidelines for HER2 status evaluation in breast carcinoma", {}),
    ("SUBTOPIC-BREAST-CARCINOMA", "Invasive Breast Carcinoma Subtypes", CurriculumLevel.SUBTOPIC, "TOPIC-BREAST-PATH", "Invasive ductal NST, invasive lobular, mucinous, and triple-negative subtypes", {}),

    ("TOPIC-GI-PATH", "Gastrointestinal & Hepatobiliary Pathology", CurriculumLevel.TOPIC, "SUBJ-SYS-PATH", "Gastric carcinoma, colorectal adenoma-carcinoma sequence, and liver cirrhosis", {}),
    ("TOPIC-LUNG-PATH", "Pulmonary & Thoracic Pathology", CurriculumLevel.TOPIC, "SUBJ-SYS-PATH", "Non-small cell lung carcinoma, small cell lung cancer, and interstitial lung diseases", {}),

    # 8. Learning Objectives
    ("LO-HER2-IHC-SCORE", "Interpret HER2 Immunohistochemistry Scores (0, 1+, 2+, 3+)", CurriculumLevel.LEARNING_OBJECTIVE, "SUBTOPIC-HER2-TESTING", "Apply ASCO/CAP 2018 criteria for complete membrane staining and reflex FISH testing.", {"competency": "ONCOPATH-BR-01"}),
    ("LO-APOPTOSIS-BCL2", "Differentiate Pro- vs Anti-apoptotic BCL2 Family Members", CurriculumLevel.LEARNING_OBJECTIVE, "SUBTOPIC-APOPTOSIS", "Recall roles of BCL2, BCL-XL vs BAX, BAK, and BH3-only sensors (BIM, PUMA).", {"competency": "GENPATH-CI-02"}),
]

# Cross-Course Curriculum Mappings (One Topic -> Multiple Courses with differing depth)
COURSE_TOPIC_MAPPINGS = [
    # Breast Pathology across all 4 courses:
    ("DM-ONCOPATH", "TOPIC-BREAST-PATH", DepthLevel.SUPER_SPECIALTY, 0.20, "DM-BR-01"),
    ("MD-PATH", "TOPIC-BREAST-PATH", DepthLevel.POSTGRADUATE, 0.10, "MD-BR-01"),
    ("NEET-PG", "TOPIC-BREAST-PATH", DepthLevel.POSTGRADUATE, 0.08, "NEET-BR-01"),
    ("MBBS-PATH", "TOPIC-BREAST-PATH", DepthLevel.UNDERGRADUATE, 0.05, "PE9.1"),

    # HER2 Testing across courses:
    ("DM-ONCOPATH", "SUBTOPIC-HER2-TESTING", DepthLevel.SUPER_SPECIALTY, 0.10, "DM-BR-HER2"),
    ("MD-PATH", "SUBTOPIC-HER2-TESTING", DepthLevel.POSTGRADUATE, 0.05, "MD-BR-HER2"),

    # Cell Injury & Apoptosis across courses:
    ("MBBS-PATH", "TOPIC-CELL-INJURY", DepthLevel.UNDERGRADUATE, 0.15, "PE1.1"),
    ("MD-PATH", "TOPIC-CELL-INJURY", DepthLevel.POSTGRADUATE, 0.10, "MD-GEN-01"),
    ("NEET-PG", "TOPIC-CELL-INJURY", DepthLevel.POSTGRADUATE, 0.12, "NEET-GEN-01"),

    # Lymphomas across courses:
    ("DM-ONCOPATH", "TOPIC-LYMPHOMAS", DepthLevel.SUPER_SPECIALTY, 0.25, "DM-HEM-LYMPH"),
    ("MD-PATH", "TOPIC-LYMPHOMAS", DepthLevel.POSTGRADUATE, 0.15, "MD-HEM-LYMPH"),
    ("NEET-PG", "TOPIC-LYMPHOMAS", DepthLevel.POSTGRADUATE, 0.10, "NEET-HEM-LYMPH"),
]


def seed_curriculum(engine) -> None:
    """Seeds courses, users, knowledge domain hierarchy, and cross-course mappings."""
    with session_scope(engine) as session:
        # 1. Seed Users
        for user_data in INITIAL_USERS:
            existing = session.query(User).filter_by(email=user_data["email"]).first()
            if not existing:
                user = User(**user_data)
                session.add(user)
                logger.info(f"Seeded user: {user_data['email']} ({user_data['role'].value})")

        # 2. Seed Sources
        existing_sources = {s.short_name: s for s in session.query(Source).all()}
        for src_data in FOUNDATIONAL_SOURCES:
            if src_data["short_name"] not in existing_sources:
                source = Source(**src_data)
                session.add(source)
                session.flush()
                existing_sources[src_data["short_name"]] = source
                logger.info(f"Seeded source: {src_data['title']}")

        # 3. Seed Sample Source Document & Chunks (Robbins Chapter 6)
        robbins = existing_sources.get("robbins_pathology")
        if robbins:
            existing_doc = session.query(SourceDocument).filter_by(source_id=robbins.id, chapter_number=6).first()
            if not existing_doc:
                doc = SourceDocument(
                    source_id=robbins.id,
                    title="Chapter 6: Neoplasia",
                    edition="10th Edition",
                    chapter_number=6,
                    page_start=265,
                    page_end=340,
                    metadata_json={"sections": ["Hallmarks of Cancer", "Oncogenes", "Tumor Suppressors"]},
                )
                session.add(doc)
                session.flush()

                # Add sample chunk for RAG / Evidence
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=1,
                    section_heading="HER2 in Breast Carcinoma",
                    page_number=285,
                    content="Amplification of ERBB2 (HER2) occurs in approximately 15% to 20% of breast cancers. These tumors are sensitive to targeted therapy with anti-HER2 antibodies (e.g., trastuzumab).",
                    content_hash="her2_sample_chunk_hash_001",
                    metadata_json={"keywords": ["HER2", "ERBB2", "trastuzumab", "breast carcinoma"]},
                )
                session.add(chunk)
                logger.info("Seeded sample SourceDocument & DocumentChunk (Robbins Chapter 6)")

        # 4. Seed Courses
        course_map: Dict[str, Course] = {}
        for course_data in INITIAL_COURSES:
            existing_course = session.query(Course).filter_by(code=course_data["code"]).first()
            if not existing_course:
                course = Course(**course_data)
                session.add(course)
                session.flush()
                course_map[course_data["code"]] = course
                logger.info(f"Seeded course: {course_data['code']} - {course_data['name']}")
            else:
                course_map[course_data["code"]] = existing_course

        # 5. Seed Canonical Knowledge Domain Tree
        node_map: Dict[str, CurriculumTopic] = {}
        for code, name, level, parent_code, description, metadata in CURRICULUM_TREE:
            existing_node = session.query(CurriculumTopic).filter_by(code=code).first()
            if not existing_node:
                parent_id = node_map[parent_code].id if parent_code and parent_code in node_map else None
                if parent_code and not parent_id:
                    parent_db = session.query(CurriculumTopic).filter_by(code=parent_code).first()
                    parent_id = parent_db.id if parent_db else None

                node = CurriculumTopic(
                    code=code,
                    name=name,
                    level=level,
                    parent_id=parent_id,
                    description=description,
                    metadata_json=metadata,
                )
                session.add(node)
                session.flush()
                node_map[code] = node
                logger.info(f"Seeded knowledge domain node [{level.value}]: {code} ({name})")
            else:
                node_map[code] = existing_node

        # 6. Seed Cross-Course Curriculum Mappings
        for course_code, topic_code, depth, weightage, comp_code in COURSE_TOPIC_MAPPINGS:
            course = course_map.get(course_code)
            topic = node_map.get(topic_code)
            if course and topic:
                existing_map = session.query(CourseCurriculumMapping).filter_by(
                    course_id=course.id, topic_id=topic.id
                ).first()
                if not existing_map:
                    mapping = CourseCurriculumMapping(
                        course_id=course.id,
                        topic_id=topic.id,
                        depth_level=depth,
                        exam_weightage=weightage,
                        is_core=True,
                        competency_code=comp_code,
                    )
                    session.add(mapping)
                    logger.info(f"Mapped {topic_code} -> {course_code} (Depth: {depth.value}, Weight: {weightage*100:.0f}%)")


if __name__ == "__main__":
    eng = get_engine()
    init_db(engine=eng)
    seed_curriculum(eng)
