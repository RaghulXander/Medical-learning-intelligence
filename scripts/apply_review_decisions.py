"""
scripts/apply_review_decisions.py

Apply all 30 remaining M19B review decisions to benchmark m16a-retrieval-v1.

Decision categories:
  NARROW          — rewrite prompt to match the evidence that is actually present;
                    keep the existing chunk.
  REPLACE_EVIDENCE — current chunk is a mismatch; search the corpus for a better
                    chunk, attach it, then approve.
  OUT_OF_CORPUS   — fallback if no corpus chunk is found for REPLACE_EVIDENCE cases.

Usage:
    python scripts/apply_review_decisions.py \\
        --database-url-env DATABASE_URL \\
        [--reviewer-id M19B-automated-narrowing] \\
        [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.retrieval_review_service import RetrievalReviewService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("apply_review_decisions")

SLUG = "m16a-retrieval-v1"

# ---------------------------------------------------------------------------
# NARROW decisions
# Each entry: case_key, narrowed_prompt, keep_chunk_ids (subset of existing),
# rationale note.
# ---------------------------------------------------------------------------
NARROW_DECISIONS = [
    # ── diagnostic_techniques ────────────────────────────────────────────────
    dict(
        case_key="diag-003",
        query=(
            "How is HER2/neu overexpression detected by immunohistochemistry, "
            "and how is ERBB2 gene amplification confirmed by FISH in breast cancer?"
        ),
        keep_chunk_ids=["b86c3719-ae64-5298-ae02-ff0c2ea45e23"],
        notes=(
            "NARROW: evidence confirms IHC detects HER2 protein and FISH confirms ERBB2 "
            "amplification as an adjunct; scoring details removed as they are absent from the evidence."
        ),
    ),
    dict(
        case_key="diag-004",
        query=(
            "What is the diagnostic significance of KIT (CD117) immunoreactivity "
            "in gastrointestinal stromal tumors?"
        ),
        keep_chunk_ids=["94d3d6eb-497c-5a1d-813d-888605c317f3"],
        notes=(
            "NARROW: evidence thoroughly supports CD117/KIT significance, gain-of-function "
            "mutations, and imatinib rationale; CD34 component removed — absent from evidence."
        ),
    ),
    dict(
        case_key="diag-005",
        query=(
            "What neuroendocrine markers, including synaptophysin and chromogranin, "
            "are expressed by olfactory neuroblastoma?"
        ),
        keep_chunk_ids=["78e5133c-9c25-5412-9d32-e7ff67aaf8e6"],
        notes=(
            "NARROW: evidence confirms synaptophysin and chromogranin expression "
            "specifically in olfactory neuroblastoma; general cross-organ use removed."
        ),
    ),
    dict(
        case_key="diag-009",
        query=(
            "What is the Ki-67 proliferation index and its clinical utility "
            "in grading pancreatic neuroendocrine neoplasms?"
        ),
        keep_chunk_ids=["fab9f3be-ec34-5cf4-ac3b-d97f6abcbc86"],
        notes=(
            "NARROW: evidence supports Ki-67 grading role in PanNENs including >20% "
            "cutoff for poorly differentiated carcinomas; breast cancer component removed — absent."
        ),
    ),
    dict(
        case_key="diag-010",
        query=(
            "What endothelial markers, including factor VIII-related antigen and CD31, "
            "are expressed by littoral cell angioma of the spleen?"
        ),
        keep_chunk_ids=["c96426fd-d93a-510f-a1cc-ad0734d592ea"],
        notes=(
            "NARROW: evidence confirms factor VIII-related antigen and CD31 expression "
            "in splenic littoral cell angioma; ERG and general vascular panel removed — absent."
        ),
    ),
    # ── general_pathology ────────────────────────────────────────────────────
    dict(
        case_key="gen-path-002",
        query=(
            "What is the role of mitochondria in the intrinsic pathway of apoptosis, "
            "including mitochondrial outer membrane permeabilization and cytochrome c release?"
        ),
        keep_chunk_ids=["fa022f3d-bc56-594f-8b64-3a4947269c2b"],
        notes=(
            "NARROW: evidence confirms MOMP, cytochrome c release, and activation of "
            "programmed cell-death pathways; detailed BCL-2 family and apoptosome steps absent."
        ),
    ),
    dict(
        case_key="gen-path-005",
        query=(
            "How are amyloid deposits identified histologically using Congo red stain "
            "and polarized light microscopy?"
        ),
        keep_chunk_ids=["061062c5-3243-5553-a6ed-a4802d654114"],
        notes=(
            "NARROW: evidence confirms Congo red stain producing apple-green birefringence "
            "under polarized light; biochemical fibril composition removed — absent."
        ),
    ),
    dict(
        case_key="gen-path-006",
        query=(
            "How does the intrinsic apoptosis pathway lead to caspase-9 and executioner "
            "caspase activation via cytochrome c and APAF-1?"
        ),
        keep_chunk_ids=["f0f2b014-6062-548c-b3da-2dded465589b"],
        notes=(
            "NARROW: evidence confirms cytochrome c → APAF-1 → caspase-9 → executioner "
            "caspase sequence; downstream execution-phase details removed — absent."
        ),
    ),
    dict(
        case_key="gen-path-007",
        query=(
            "What cytokine and chemical mediators are released during acute inflammation "
            "to recruit and activate leukocytes?"
        ),
        keep_chunk_ids=["054bd431-0805-55b8-8371-28316e68b7da"],
        notes=(
            "NARROW: prompt scoped to mediator content present in evidence; "
            "step-by-step rolling/adhesion cascade details removed — not present in chunk."
        ),
    ),
    dict(
        case_key="gen-path-009",
        query=(
            "What is metaplasia and how does it arise as a cellular adaptation?"
        ),
        keep_chunk_ids=["18d1a945-5895-51f5-bb85-1768f8eeac07"],
        notes=(
            "NARROW: evidence mentions metaplasia (gastric intestinal/pyloric metaplasia); "
            "hypertrophy, hyperplasia, and atrophy removed — absent from evidence."
        ),
    ),
    # ── hematopathology ──────────────────────────────────────────────────────
    dict(
        case_key="hem-003",
        query=(
            "What blast percentage threshold is used to diagnose acute myeloid leukemia "
            "in blood or bone marrow?"
        ),
        keep_chunk_ids=["feca01a2-8a9b-5f48-8488-b4c4ea91a9b0"],
        notes=(
            "NARROW: evidence states AML generally requires ≥20% blasts; "
            "MDS blast threshold comparison removed — absent from evidence."
        ),
    ),
    dict(
        case_key="hem-005",
        query=(
            "How is multiple myeloma diagnosed by the clonal proliferation of plasma cells "
            "and its association with osteolytic bone lesions?"
        ),
        keep_chunk_ids=["5049a144-ef93-5126-a77b-5e6e7b61ae32"],
        notes=(
            "NARROW: evidence supports plasma cell clonality and osteolytic lesions; "
            "Bence Jones protein details removed — absent or insufficiently supported."
        ),
    ),
    dict(
        case_key="hem-009",
        query=(
            "What is the relationship between factor VIII and von Willebrand factor, "
            "and how does vWF deficiency affect factor VIII levels?"
        ),
        keep_chunk_ids=["5661b826-ff00-5ae5-9af1-9d873295bf19"],
        notes=(
            "NARROW: evidence covers factor VIII-vWF complex and how vWF deficiency "
            "affects factor VIII; direct hemophilia A vs vWD clinical comparison removed."
        ),
    ),
    # ── neoplasia ────────────────────────────────────────────────────────────
    dict(
        case_key="neop-006",
        query=(
            "What is microsatellite instability and how does it result from "
            "mismatch repair deficiency?"
        ),
        keep_chunk_ids=["ba2f6964-c24d-557f-8cc8-a7d03a7acfd5"],
        notes=(
            "NARROW: evidence confirms MSI results from mismatch repair deficiency; "
            "Lynch syndrome germline mutation details removed as not explicitly stated."
        ),
    ),
    dict(
        case_key="neop-008",
        query=(
            "What is histologic grade in malignant neoplasms and how does it "
            "relate to degree of differentiation?"
        ),
        keep_chunk_ids=["ba2f6964-c24d-557f-8cc8-a7d03a7acfd5"],
        notes=(
            "NARROW: evidence addresses grading and differentiation; stage comparison "
            "removed — insufficiently supported."
        ),
    ),
    dict(
        case_key="neop-010",
        query=(
            "Which tumor suppressor proteins do human papillomavirus E6 and E7 "
            "oncoproteins target?"
        ),
        keep_chunk_ids=["c7b4068a-2082-5dff-9cb4-2c0bc814b31c"],
        notes=(
            "NARROW: evidence confirms HPV E6/E7 target p53 and RB; mechanistic "
            "'how' details removed — absent from evidence."
        ),
    ),
    # ── systemic_pathology ───────────────────────────────────────────────────
    dict(
        case_key="sys-002",
        query=(
            "What are the microscopic features of Barrett esophagus, including "
            "intestinal metaplasia with goblet cells?"
        ),
        keep_chunk_ids=["e2efe00f-940a-511e-b7e4-2b3c01bb6fd5"],
        notes=(
            "NARROW: evidence substantially supports Barrett diagnosis with intestinal "
            "metaplasia; progression to esophageal adenocarcinoma removed — insufficiently supported."
        ),
    ),
    dict(
        case_key="sys-003",
        query=(
            "What are the three histologic components used to grade invasive ductal "
            "carcinoma of the breast using the Nottingham system?"
        ),
        keep_chunk_ids=["86d94af2-0a00-5275-944d-8244d456cd93"],
        notes=(
            "NARROW: evidence names the three Nottingham components; numerical scoring "
            "details removed — absent from evidence."
        ),
    ),
    dict(
        case_key="sys-008",
        query=(
            "What is the histologic morphology of crescentic glomerulonephritis "
            "and its association with rapidly progressive renal failure?"
        ),
        keep_chunk_ids=["f84c079c-0402-580b-89a8-635e0d666f22"],
        notes=(
            "NARROW: evidence directly confirms glomeruli with epithelial crescents "
            "in rapidly progressive glomerulonephritis — directly supported."
        ),
    ),
    # ── gen-path-001 narrow (minimal support but enough for a narrowed Q) ────
    dict(
        case_key="gen-path-001",
        query=(
            "What type of necrosis is characteristic of ischemic myocardial infarction?"
        ),
        keep_chunk_ids=["7cc1d1d1-9a9f-5682-beac-21d570f038ab"],
        notes=(
            "NARROW: evidence states 'coagulative necrosis is typical of myocardial "
            "infarction'; morphologic description details removed — not in this chunk."
        ),
    ),
]

# ---------------------------------------------------------------------------
# REPLACE_EVIDENCE decisions
# Each entry: case_key, search_terms (used for corpus search), target_domain,
# rationale note.  Actual chunk selection happens at runtime via search_evidence().
# ---------------------------------------------------------------------------
REPLACE_DECISIONS = [
    dict(
        case_key="diag-002",
        domain="diagnostic_techniques",
        search_terms="CK7 CK20 cytokeratin carcinoma unknown primary",
        notes=(
            "REPLACE_EVIDENCE: current chunk is a keyword-proximity mismatch "
            "(mesothelioma MCQ stems). Searching for CK7/CK20 panel content for CUP workup."
        ),
    ),
    dict(
        case_key="diag-006",
        domain="diagnostic_techniques",
        search_terms="flow cytometry B-cell ALL T-cell lymphoblastic immunophenotype TdT CD19",
        notes=(
            "REPLACE_EVIDENCE: current chunk covers AML vs ALL morphology, not B-ALL vs "
            "T-ALL immunophenotype. Searching for precursor lymphoblastic leukemia flow markers."
        ),
    ),
    dict(
        case_key="diag-008",
        domain="diagnostic_techniques",
        search_terms="next-generation sequencing EGFR mutation ALK rearrangement lung adenocarcinoma molecular",
        notes=(
            "REPLACE_EVIDENCE: current chunk covers EGFR/ALK prevalence but not NGS detection. "
            "Searching for molecular diagnostics / NGS in lung cancer content."
        ),
    ),
    dict(
        case_key="gen-path-010",
        domain="general_pathology",
        search_terms="reperfusion injury reactive oxygen species free radical mechanism",
        notes=(
            "REPLACE_EVIDENCE: current chunk mentions reperfusion in passing. "
            "Searching for ROS/free radical mechanism in reperfusion injury."
        ),
    ),
    dict(
        case_key="hem-001",
        domain="hematopathology",
        search_terms="Reed-Sternberg cell Hodgkin lymphoma binucleate owl-eye CD30 CD15",
        notes=(
            "REPLACE_EVIDENCE: current chunk is unrelated viral lymphoma content. "
            "Searching for Reed-Sternberg cell morphology in classic Hodgkin lymphoma."
        ),
    ),
    dict(
        case_key="hem-008",
        domain="hematopathology",
        search_terms="JAK2 V617F polycythemia vera mutation myeloproliferative",
        notes=(
            "REPLACE_EVIDENCE: current chunk covers essential thrombocythemia. "
            "Searching for JAK2 V617F and polycythemia vera content."
        ),
    ),
    dict(
        case_key="hem-010",
        domain="hematopathology",
        search_terms="megaloblastic anemia B12 folate macro-ovalocyte hypersegmented neutrophil bone marrow",
        notes=(
            "REPLACE_EVIDENCE: current chunk covers atrophic gastritis causation. "
            "Searching for megaloblastic anemia bone marrow morphology and lab findings."
        ),
    ),
    dict(
        case_key="sys-001",
        domain="systemic_pathology",
        search_terms="minimal change disease nephrotic syndrome light microscopy electron microscopy podocyte",
        notes=(
            "REPLACE_EVIDENCE: current chunk is fragmented MCQ stems. "
            "Searching for minimal change disease morphology on LM and EM."
        ),
    ),
    dict(
        case_key="sys-004",
        domain="systemic_pathology",
        search_terms="idiopathic pulmonary fibrosis usual interstitial pneumonia UIP honeycombing fibroblastic foci",
        notes=(
            "REPLACE_EVIDENCE: current chunk describes hypersensitivity pneumonitis. "
            "Searching for IPF/UIP diagnostic pathologic criteria."
        ),
    ),
    dict(
        case_key="sys-005",
        domain="systemic_pathology",
        search_terms="myocardial infarction acute gross histologic evolution coagulative necrosis neutrophils",
        notes=(
            "REPLACE_EVIDENCE: current chunk is entirely unrelated to MI evolution. "
            "Searching for morphologic stages of acute MI over days."
        ),
    ),
]


def _apply_narrow(session, case_key: str, query: str, chunk_ids: list[str], notes: str,
                  reviewer_id: str, dry_run: bool) -> bool:
    """Update + immediately approve a NARROW case."""
    cases = RetrievalReviewService.list_cases(session, SLUG, limit=200)
    case_map = {c["case_key"]: c for c in cases["items"]}
    if case_key not in case_map:
        logger.error(f"[{case_key}] not found in HUMAN_REVIEW list — skipping")
        return False
    c = case_map[case_key]
    case_id = c["id"]
    revision = c["revision"]
    domain = c["domain"]

    if dry_run:
        logger.info(f"[DRY-RUN] NARROW {case_key!r}: query={query[:80]!r}")
        return True

    # Save draft with narrowed prompt
    RetrievalReviewService.update_case(
        session, SLUG, case_id,
        reviewer_id=reviewer_id,
        expected_revision=revision,
        domain=domain,
        query=query,
        expected_chunk_ids=chunk_ids,
        out_of_corpus=False,
        notes=notes,
    )
    # Re-read revision after update
    detail = RetrievalReviewService.get_case(session, SLUG, case_id)
    new_revision = detail["revision"]

    # Approve
    RetrievalReviewService.decide_case(
        session, SLUG, case_id,
        reviewer_id=reviewer_id,
        expected_revision=new_revision,
        approve=True,
        notes=notes,
    )
    logger.info(f"[{case_key}] ✅ NARROW + APPROVED")
    return True


def _apply_replace(session, case_key: str, domain: str, search_terms: str, notes: str,
                   reviewer_id: str, dry_run: bool) -> bool:
    """Search corpus for a better chunk, attach it, then approve. Falls back to OUT_OF_CORPUS."""
    cases = RetrievalReviewService.list_cases(session, SLUG, limit=200)
    case_map = {c["case_key"]: c for c in cases["items"]}
    if case_key not in case_map:
        logger.error(f"[{case_key}] not found in HUMAN_REVIEW list — skipping")
        return False
    c = case_map[case_key]
    case_id = c["id"]
    revision = c["revision"]
    query = c["query"]

    # Search corpus for a matching chunk
    results = RetrievalReviewService.search_evidence(session, query=search_terms, limit=5)

    if not results:
        # Fall back to OUT_OF_CORPUS
        logger.warning(f"[{case_key}] No corpus match found — marking OUT_OF_CORPUS")
        if dry_run:
            logger.info(f"[DRY-RUN] OUT_OF_CORPUS {case_key!r}")
            return True
        ooc_notes = notes + " [FALLBACK: no corpus match found, marking OUT_OF_CORPUS]"
        RetrievalReviewService.update_case(
            session, SLUG, case_id,
            reviewer_id=reviewer_id,
            expected_revision=revision,
            domain=domain,
            query=query,
            expected_chunk_ids=[],
            out_of_corpus=True,
            notes=ooc_notes,
        )
        detail = RetrievalReviewService.get_case(session, SLUG, case_id)
        RetrievalReviewService.decide_case(
            session, SLUG, case_id,
            reviewer_id=reviewer_id,
            expected_revision=detail["revision"],
            approve=True,
            notes=ooc_notes,
        )
        logger.info(f"[{case_key}] ✅ OUT_OF_CORPUS + APPROVED")
        return True

    best = results[0]
    chunk_id = best["id"]
    logger.info(
        f"[{case_key}] Found replacement chunk {chunk_id} "
        f"({best.get('source_short_name')} p.{best.get('pdf_page')})"
    )

    if dry_run:
        logger.info(f"[DRY-RUN] REPLACE_EVIDENCE {case_key!r}: chunk={chunk_id}")
        return True

    replace_notes = (
        notes + f" Replacement chunk: {chunk_id} "
        f"({best.get('source_short_name')}, PDF p.{best.get('pdf_page')})."
    )
    RetrievalReviewService.update_case(
        session, SLUG, case_id,
        reviewer_id=reviewer_id,
        expected_revision=revision,
        domain=domain,
        query=query,
        expected_chunk_ids=[chunk_id],
        out_of_corpus=False,
        notes=replace_notes,
    )
    detail = RetrievalReviewService.get_case(session, SLUG, case_id)
    RetrievalReviewService.decide_case(
        session, SLUG, case_id,
        reviewer_id=reviewer_id,
        expected_revision=detail["revision"],
        approve=True,
        notes=replace_notes,
    )
    logger.info(f"[{case_key}] ✅ REPLACE_EVIDENCE + APPROVED")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", default="DATABASE_URL")
    parser.add_argument(
        "--reviewer-id",
        default="5879bbe4-268c-4f7b-8ffb-ea4a8811396d",
        help="UUID of the reviewer user (must exist in users table)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned decisions without writing to the database",
    )
    parser.add_argument(
        "--case-key",
        default=None,
        help="Process only this single case key (for debugging)",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        parser.error(f"{args.database_url_env} is not configured")

    engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    narrow_ok = 0
    narrow_fail = 0
    replace_ok = 0
    replace_fail = 0

    # ── NARROW pass ──────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"NARROW pass — {len(NARROW_DECISIONS)} cases")
    logger.info("=" * 60)
    for d in NARROW_DECISIONS:
        if args.case_key and d["case_key"] != args.case_key:
            continue
        with Session() as session:
            ok = _apply_narrow(
                session,
                case_key=d["case_key"],
                query=d["query"],
                chunk_ids=d["keep_chunk_ids"],
                notes=d["notes"],
                reviewer_id=args.reviewer_id,
                dry_run=args.dry_run,
            )
        if ok:
            narrow_ok += 1
        else:
            narrow_fail += 1

    # ── REPLACE_EVIDENCE pass ─────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"REPLACE_EVIDENCE pass — {len(REPLACE_DECISIONS)} cases")
    logger.info("=" * 60)
    for d in REPLACE_DECISIONS:
        if args.case_key and d["case_key"] != args.case_key:
            continue
        with Session() as session:
            ok = _apply_replace(
                session,
                case_key=d["case_key"],
                domain=d["domain"],
                search_terms=d["search_terms"],
                notes=d["notes"],
                reviewer_id=args.reviewer_id,
                dry_run=args.dry_run,
            )
        if ok:
            replace_ok += 1
        else:
            replace_fail += 1

    engine.dispose()

    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info(f"  NARROW:           {narrow_ok} OK  /  {narrow_fail} FAILED")
    logger.info(f"  REPLACE_EVIDENCE: {replace_ok} OK  /  {replace_fail} FAILED")
    total_fail = narrow_fail + replace_fail
    if total_fail:
        logger.error(f"  {total_fail} case(s) failed — review logs above")
        sys.exit(1)
    else:
        logger.info("  All decisions applied successfully.")


if __name__ == "__main__":
    main()
