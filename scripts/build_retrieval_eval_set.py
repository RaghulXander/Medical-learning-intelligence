"""
scripts/build_retrieval_eval_set.py

Milestone 16A: Generates a bootstrap retrieval evaluation candidate dataset
(data/evaluation/retrieval/m16a_retrieval_eval_v1.jsonl) containing 55 curated medical
queries across 5 core pathology domains and deliberate out-of-corpus controls,
with each in-corpus case linked by automated term matching. These links are not
gold labels until a human reviewer verifies them against the source evidence.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "medical_exam.db"
OUTPUT_FILE = PROJECT_ROOT / "data" / "evaluation" / "retrieval" / "m16a_retrieval_eval_v1.jsonl"


def get_chunk_by_terms(conn: sqlite3.Connection, search_terms: list[str]) -> str:
    """Finds the best matching chunk ID containing as many search terms as possible."""
    cursor = conn.cursor()
    # Try all terms
    query = "SELECT id FROM document_chunks WHERE " + " AND ".join(["content LIKE ?"] * len(search_terms)) + " LIMIT 1"
    params = [f"%{term}%" for term in search_terms]
    cursor.execute(query, params)
    row = cursor.fetchone()
    if row:
        return row[0]

    # Try subsets of terms if all terms aren't in a single chunk
    for i in range(len(search_terms) - 1, 0, -1):
        query = "SELECT id FROM document_chunks WHERE " + " AND ".join(["content LIKE ?"] * i) + " LIMIT 1"
        params = [f"%{term}%" for term in search_terms[:i]]
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            return row[0]

    # Fallback to single primary term
    cursor.execute("SELECT id FROM document_chunks WHERE content LIKE ? LIMIT 1", (f"%{search_terms[0]}%",))
    row = cursor.fetchone()
    if row:
        return row[0]

    raise ValueError(f"Could not find any chunk for terms: {search_terms}")


def build_evaluation_set() -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))

    # Curated cases mapped to search terms guaranteed to be in Robbins 11th or Robbins Review
    cases_specs = [
        # --- DOMAIN: General Pathology (10 cases) ---
        {
            "id": "gen-path-001",
            "domain": "general_pathology",
            "query": "What are the characteristic morphologic features of coagulative necrosis in ischemic tissue?",
            "terms": ["coagulative necrosis", "ischemic", "architecture"],
        },
        {
            "id": "gen-path-002",
            "domain": "general_pathology",
            "query": "What are the molecular mechanisms of the mitochondrial intrinsic pathway of apoptosis and role of cytochrome c?",
            "terms": ["mitochondrial", "cytochrome c", "apoptosis"],
        },
        {
            "id": "gen-path-003",
            "domain": "general_pathology",
            "query": "How does liquefactive necrosis differ from coagulative necrosis in central nervous system infarction?",
            "terms": ["liquefactive necrosis", "brain"],
        },
        {
            "id": "gen-path-004",
            "domain": "general_pathology",
            "query": "What is the mechanism of dystrophic calcification versus metastatic calcification?",
            "terms": ["dystrophic calcification", "metastatic calcification"],
        },
        {
            "id": "gen-path-005",
            "domain": "general_pathology",
            "query": "What is the biochemical composition of amyloid fibrils and characteristic Congo red birefringence under polarized light?",
            "terms": ["Congo red", "apple-green birefringence", "amyloid"],
        },
        {
            "id": "gen-path-006",
            "domain": "general_pathology",
            "query": "What role do caspases play in the execution phase of programmed cell death?",
            "terms": ["caspases", "executioner", "apoptosis"],
        },
        {
            "id": "gen-path-007",
            "domain": "general_pathology",
            "query": "What are the stages of leukocyte extravasation during acute inflammation, including rolling and adhesion molecules?",
            "terms": ["selectin", "integrin", "extravasation"],
        },
        {
            "id": "gen-path-008",
            "domain": "general_pathology",
            "query": "What are the histologic hallmarks of chronic granulomatous inflammation and multinucleated giant cells?",
            "terms": ["granulomatous inflammation", "epithelioid", "Langhans"],
        },
        {
            "id": "gen-path-009",
            "domain": "general_pathology",
            "query": "What are the cellular adaptations of hypertrophy, hyperplasia, atrophy, and metaplasia?",
            "terms": ["hypertrophy", "hyperplasia", "atrophy", "metaplasia"],
        },
        {
            "id": "gen-path-010",
            "domain": "general_pathology",
            "query": "How does free radical generation and reactive oxygen species contribute to reperfusion injury?",
            "terms": ["reperfusion injury", "reactive oxygen species"],
        },

        # --- DOMAIN: Neoplasia & Tumor Biology (10 cases) ---
        {
            "id": "neop-001",
            "domain": "neoplasia",
            "query": "What is the two-hit hypothesis of Knudson in retinoblastoma and function of the RB protein?",
            "terms": ["retinoblastoma", "Knudson", "two-hit"],
        },
        {
            "id": "neop-002",
            "domain": "neoplasia",
            "query": "What is the role of TP53 as guardian of the genome in inducing cell cycle arrest and apoptosis?",
            "terms": ["TP53", "guardian of the genome", "p21"],
        },
        {
            "id": "neop-003",
            "domain": "neoplasia",
            "query": "How does the Warburg effect characterize aerobic glycolysis in neoplastic cells?",
            "terms": ["Warburg effect", "aerobic glycolysis"],
        },
        {
            "id": "neop-004",
            "domain": "neoplasia",
            "query": "What is the mechanism of microRNA dysregulation and epigenetic silencing in carcinogenesis?",
            "terms": ["DNA methylation", "epigenetic", "carcinogenesis"],
        },
        {
            "id": "neop-005",
            "domain": "neoplasia",
            "query": "What are the steps of the metastatic cascade, including down-regulation of E-cadherin and invasion of extracellular matrix?",
            "terms": ["E-cadherin", "metastasis", "invasion", "basement membrane"],
        },
        {
            "id": "neop-006",
            "domain": "neoplasia",
            "query": "How does mismatch repair gene deficiency lead to microsatellite instability in Lynch syndrome?",
            "terms": ["mismatch repair", "microsatellite instability", "Lynch"],
        },
        {
            "id": "neop-007",
            "domain": "neoplasia",
            "query": "What is the role of VEGF and basic fibroblast growth factor in tumor-induced angiogenesis?",
            "terms": ["VEGF", "angiogenesis", "endothelial"],
        },
        {
            "id": "neop-008",
            "domain": "neoplasia",
            "query": "What is the difference between histologic grade and clinical stage in assessing malignant neoplasms?",
            "terms": ["grading", "staging", "TNM"],
        },
        {
            "id": "neop-009",
            "domain": "neoplasia",
            "query": "What is the oncogenic driver mechanism of BCR-ABL fusion kinase resulting from t(9;22)?",
            "terms": ["BCR-ABL", "Philadelphia chromosome"],
        },
        {
            "id": "neop-010",
            "domain": "neoplasia",
            "query": "How does human papillomavirus E6 and E7 oncoproteins inactivate p53 and RB?",
            "terms": ["HPV", "E6", "E7", "RB"],
        },

        # --- DOMAIN: Hematopathology (10 cases) ---
        {
            "id": "hem-001",
            "domain": "hematopathology",
            "query": "What are the diagnostic cytologic features of Reed-Sternberg cells in classic Hodgkin lymphoma?",
            "terms": ["Reed-Sternberg", "Hodgkin lymphoma"],
        },
        {
            "id": "hem-002",
            "domain": "hematopathology",
            "query": "What is the characteristic t(8;14) translocation and starry sky microscopic appearance of Burkitt lymphoma?",
            "terms": ["Burkitt lymphoma", "MYC", "starry sky"],
        },
        {
            "id": "hem-003",
            "domain": "hematopathology",
            "query": "What are the diagnostic bone marrow blast criteria for acute myeloid leukemia versus myelodysplastic syndromes?",
            "terms": ["myeloblasts", "acute myeloid leukemia", "Auer rods"],
        },
        {
            "id": "hem-004",
            "domain": "hematopathology",
            "query": "What is the genetic hallmark t(14;18) involving BCL2 translocation in follicular lymphoma?",
            "terms": ["follicular lymphoma", "t(14;18)", "BCL2"],
        },
        {
            "id": "hem-005",
            "domain": "hematopathology",
            "query": "How does multiple myeloma present with monoclonal paraprotein, osteolytic lesions, and Bence Jones proteinuria?",
            "terms": ["multiple myeloma", "plasma cells", "Bence Jones"],
        },
        {
            "id": "hem-006",
            "domain": "hematopathology",
            "query": "What is the pathogenesis of immune thrombocytopenic purpura and anti-platelet glycoprotein antibodies?",
            "terms": ["thrombocytopenic purpura", "platelet", "spleen"],
        },
        {
            "id": "hem-007",
            "domain": "hematopathology",
            "query": "What are the peripheral blood smear findings in microangiopathic hemolytic anemia, including schistocytes?",
            "terms": ["schistocytes", "microangiopathic hemolytic anemia"],
        },
        {
            "id": "hem-008",
            "domain": "hematopathology",
            "query": "What is the molecular pathogenesis of the JAK2 V617F mutation in polycythemia vera?",
            "terms": ["JAK2", "V617F", "polycythemia vera"],
        },
        {
            "id": "hem-009",
            "domain": "hematopathology",
            "query": "What is the hematologic and clinical distinction between hemophilia A and von Willebrand disease?",
            "terms": ["von Willebrand", "factor VIII", "hemophilia"],
        },
        {
            "id": "hem-010",
            "domain": "hematopathology",
            "query": "What are the laboratory findings and bone marrow morphology in megaloblastic anemia from B12 or folate deficiency?",
            "terms": ["megaloblastic anemia", "vitamin B12", "hypersegmented"],
        },

        # --- DOMAIN: Systemic & Organ-Specific Pathology (10 cases) ---
        {
            "id": "sys-001",
            "domain": "systemic_pathology",
            "query": "What is the histologic morphology of minimal change disease on light versus electron microscopy?",
            "terms": ["minimal change disease", "effacement", "foot processes"],
        },
        {
            "id": "sys-002",
            "domain": "systemic_pathology",
            "query": "What are the microscopic features of Barrett esophagus and its progression to esophageal adenocarcinoma?",
            "terms": ["Barrett esophagus", "goblet cells", "adenocarcinoma"],
        },
        {
            "id": "sys-003",
            "domain": "systemic_pathology",
            "query": "How is invasive ductal carcinoma of the breast graded using the Nottingham histologic score?",
            "terms": ["Nottingham", "tubule formation", "mitotic"],
        },
        {
            "id": "sys-004",
            "domain": "systemic_pathology",
            "query": "What are the diagnostic pathologic criteria for idiopathic pulmonary fibrosis and usual interstitial pneumonia pattern?",
            "terms": ["usual interstitial pneumonia", "fibroblastic foci", "honeycombing"],
        },
        {
            "id": "sys-005",
            "domain": "systemic_pathology",
            "query": "What are the gross and histologic evolution stages of acute myocardial infarction over 1 to 14 days?",
            "terms": ["myocardial infarction", "coagulation necrosis", "granulation tissue"],
        },
        {
            "id": "sys-006",
            "domain": "systemic_pathology",
            "query": "What is the histopathologic distinction between Crohn disease and ulcerative colitis?",
            "terms": ["Crohn disease", "ulcerative colitis", "transmural", "granulomas"],
        },
        {
            "id": "sys-007",
            "domain": "systemic_pathology",
            "query": "What are the microscopic hallmarks of papillary thyroid carcinoma including Orphan Annie nuclei and psammoma bodies?",
            "terms": ["papillary thyroid carcinoma", "Orphan Annie", "psammoma bodies"],
        },
        {
            "id": "sys-008",
            "domain": "systemic_pathology",
            "query": "What is the morphology of crescentic glomerulonephritis and rapidly progressive renal failure?",
            "terms": ["crescents", "rapidly progressive glomerulonephritis", "Bowman"],
        },
        {
            "id": "sys-009",
            "domain": "systemic_pathology",
            "query": "How do Mallory-Denk bodies and ballooning degeneration appear in alcoholic steatohepatitis?",
            "terms": ["Mallory-Denk", "steatohepatitis", "ballooning"],
        },
        {
            "id": "sys-010",
            "domain": "systemic_pathology",
            "query": "What is the histologic architecture and Gleason grading system of prostate adenocarcinoma?",
            "terms": ["Gleason", "prostate adenocarcinoma", "cribriform"],
        },

        # --- DOMAIN: Diagnostic Techniques & IHC (10 cases) ---
        {
            "id": "diag-001",
            "domain": "diagnostic_techniques",
            "query": "What immunohistochemical panel is used to differentiate adenocarcinoma from malignant mesothelioma?",
            "terms": ["calretinin", "WT1", "mesothelioma", "adenocarcinoma"],
        },
        {
            "id": "diag-002",
            "domain": "diagnostic_techniques",
            "query": "What is the utility of cytokeratin 7 and cytokeratin 20 (CK7/CK20) expression profile in carcinomas of unknown primary?",
            "terms": ["cytokeratin 7", "cytokeratin 20", "carcinoma"],
        },
        {
            "id": "diag-003",
            "domain": "diagnostic_techniques",
            "query": "How is HER2/neu overexpression and gene amplification evaluated by immunohistochemistry and FISH?",
            "terms": ["HER2", "immunohistochemistry", "FISH"],
        },
        {
            "id": "diag-004",
            "domain": "diagnostic_techniques",
            "query": "What is the diagnostic significance of CD34 and KIT (CD117) immunoreactivity in gastrointestinal stromal tumors?",
            "terms": ["CD117", "gastrointestinal stromal tumor", "KIT"],
        },
        {
            "id": "diag-005",
            "domain": "diagnostic_techniques",
            "query": "What immunohistochemical markers are used to identify neuroendocrine differentiation, including synaptophysin and chromogranin?",
            "terms": ["synaptophysin", "chromogranin", "neuroendocrine"],
        },
        {
            "id": "diag-006",
            "domain": "diagnostic_techniques",
            "query": "How does flow cytometry immunophenotyping differentiate B-cell ALL from T-cell ALL?",
            "terms": ["flow cytometry", "immunophenotyping", "lymphoblasts"],
        },
        {
            "id": "diag-007",
            "domain": "diagnostic_techniques",
            "query": "What is the diagnostic utility of S100 and SOX10 in confirming metastatic melanoma?",
            "terms": ["S100", "melanoma", "melanocytic"],
        },
        {
            "id": "diag-008",
            "domain": "diagnostic_techniques",
            "query": "What is the role of next-generation sequencing in detecting EGFR mutations and ALK rearrangements in lung adenocarcinoma?",
            "terms": ["EGFR", "ALK", "adenocarcinoma", "lung"],
        },
        {
            "id": "diag-009",
            "domain": "diagnostic_techniques",
            "query": "What is the Ki-67 proliferation index and its clinical utility in neuroendocrine tumors and breast cancer?",
            "terms": ["Ki-67", "proliferation index", "mitotic"],
        },
        {
            "id": "diag-010",
            "domain": "diagnostic_techniques",
            "query": "What are the common immunohistochemical markers for vascular tumors, including CD31 and ERG?",
            "terms": ["CD31", "endothelial", "vascular"],
        },

        # --- DOMAIN: Out-of-Corpus Controls (5 cases) ---
        {
            "id": "ctrl-001",
            "domain": "out_of_corpus",
            "query": "What is the recommended pediatric antibiotic dosing schedule for amoxicillin in acute otitis media?",
            "out_of_corpus": True,
        },
        {
            "id": "ctrl-002",
            "domain": "out_of_corpus",
            "query": "What are the diagnostic DSM-5 criteria and psychiatric pharmacological treatments for bipolar I manic episodes?",
            "out_of_corpus": True,
        },
        {
            "id": "ctrl-003",
            "domain": "out_of_corpus",
            "query": "How is a laparoscopic appendectomy performed step-by-step including trocar placement and appendiceal artery ligation?",
            "out_of_corpus": True,
        },
        {
            "id": "ctrl-004",
            "domain": "out_of_corpus",
            "query": "What are the guidelines for dental implant placement depth and osseointegration mechanical torque measurements?",
            "out_of_corpus": True,
        },
        {
            "id": "ctrl-005",
            "domain": "out_of_corpus",
            "query": "What are the ventilator management tidal volume settings for acute respiratory distress syndrome in the ICU?",
            "out_of_corpus": True,
        },
    ]

    eval_cases = []
    for spec in cases_specs:
        is_ooc = spec.get("out_of_corpus", False)
        if is_ooc:
            eval_cases.append({
                "id": spec["id"],
                "domain": spec["domain"],
                "query": spec["query"],
                "expected_chunk_ids": [],
                "out_of_corpus": True,
                "reviewer": "automated-bootstrap",
                "verification_status": "AUTO_BOOTSTRAP_UNVERIFIED",
            })
        else:
            chunk_id = get_chunk_by_terms(conn, spec["terms"])
            eval_cases.append({
                "id": spec["id"],
                "domain": spec["domain"],
                "query": spec["query"],
                "expected_chunk_ids": [chunk_id],
                "out_of_corpus": False,
                "reviewer": "automated-bootstrap",
                "verification_status": "AUTO_BOOTSTRAP_UNVERIFIED",
            })

    conn.close()
    return eval_cases


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    cases = build_evaluation_set()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")

    print(f"Generated {len(cases)} unverified benchmark candidates in {OUTPUT_FILE}")
    print("A human reviewer must verify every expected chunk before evaluation.")


if __name__ == "__main__":
    main()
