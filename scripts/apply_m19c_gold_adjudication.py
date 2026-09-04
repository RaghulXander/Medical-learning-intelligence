"""Apply audited human gold-standard evidence adjudications for Milestone 19C."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
database_url = os.environ.get("DATABASE_URL")
engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)

from backend.services.retrieval_review_service import RetrievalReviewService
from database.models import RetrievalBenchmark, RetrievalBenchmarkCase

ADJUDICATIONS = {
    "diag-002": {
        "expected_chunks": ["aa2dc1bc-d261-58ad-a252-21e3f515f457", "dc6336e7-e5a6-52f1-bd4a-03ba2a18b7d7"],
        "notes": "Adjudicated to Sternberg Review 2nd p.605, p.608 covering CK7/CK20 diagnostic IHC profiles in unknown primary differentials."
    },
    "diag-003": {
        "expected_chunks": ["fd81fcab-2b53-5ae0-9af3-bdb9e7acc1cf", "fc26b4ff-192e-52f3-86fb-09e72f86f0a8"],
        "notes": "Adjudicated to Robbins Basis 11th p.976-977 Fig 23.19 and Table 23.4 covering HER2 IHC scoring and FISH ERBB2 amplification."
    },
    "diag-006": {
        "expected_chunks": [
            "26535c44-582a-5758-b1f1-2b54026a29b6",
            "1ecbc0a4-688d-5f5a-b105-957b4696f4b4",
            "de948f45-fc91-5783-9094-1d2d3b5de298"
        ],
        "notes": "Adjudicated to Robbins Basis 11th p.555-558 covering flow cytometry immunophenotyping differentiation of B-ALL and T-ALL."
    },
    "diag-008": {
        "expected_chunks": ["b3a7e8a4-071e-569a-843b-726a7d3a2595", "ba07719f-0619-509c-b966-40ec8ea94116", "1dafc8b7-657e-5cb6-bbb3-f95b56365df0"],
        "notes": "Adjudicated to Robbins Basis 11th p.180-181, p.314 covering NGS molecular diagnostic testing for EGFR and ALK in lung carcinoma."
    },
    "gen-path-001": {
        "expected_chunks": ["4a9f6df2-7a16-5c82-8018-4aef40448a66", "6dc5df03-841e-5369-859b-a3bcc9102a6a", "7cc1d1d1-9a9f-5682-beac-21d570f038ab"],
        "notes": "Adjudicated to Robbins Review p.180, Robbins Basis p.54, Robbins Review p.35 covering coagulative necrosis in myocardial infarction."
    },
    "gen-path-005": {
        "expected_chunks": ["37a3d85b-2e10-5c0f-92c2-ac4d07471c5d", "c51c8fb9-1045-5a32-9277-5f89ab6e7cc6", "061062c5-3243-5553-a6ed-a4802d654114"],
        "notes": "Adjudicated to Robbins Basis 11th p.249-250, p.539 covering Congo red apple-green birefringence under polarized light."
    },
    "gen-path-006": {
        "expected_chunks": ["69375534-2459-5806-8109-2f87d772e012", "49404e96-fa49-5af1-a77d-dcd5bfbb6dae"],
        "notes": "Adjudicated to Robbins Basis 11th p.58-59 covering mitochondrial intrinsic apoptosis pathway, Cytochrome c, APAF-1, Caspase-9."
    },
    "gen-path-009": {
        "expected_chunks": ["6f0f7c59-7cc7-51ce-add6-793572683db9", "d30798d4-4a0d-5afb-a4c4-9b1dd93b198b", "48a63347-ae96-575c-9ee6-3401e51854d5"],
        "notes": "Adjudicated to Robbins Basis 11th p.71, p.79, p.257 covering metaplasia cellular adaptation mechanisms and clinical examples."
    },
    "gen-path-010": {
        "expected_chunks": ["66292be5-b1f4-5c20-a52d-056dc5a0f6db", "4a548f12-c922-59ef-8c24-6eaf26d20534", "e8fe07e7-fff0-5379-b8b8-5a9a89383014"],
        "notes": "Adjudicated to Robbins Basis 11th p.63-65 covering reactive oxygen species (ROS) and free radical pathology in reperfusion injury."
    },
    "hem-001": {
        "expected_chunks": ["eea9f9ad-cb45-59bf-88fa-6e15cede30e4", "d0962cf2-6b15-5e29-8734-770628e49cff", "35aec007-afea-5c7d-8b1c-e32cf3c4f1e9"],
        "notes": "Adjudicated to Robbins Basis 11th p.573-575 Fig 13.25 covering diagnostic Reed-Sternberg cell morphology in Hodgkin lymphoma."
    },
    "hem-008": {
        "expected_chunks": ["39aac053-f544-50cf-8d60-366b0a148145", "4f976096-39bb-5d46-b341-e4ed9bf0689c", "30d07b1e-f1c1-5ccf-8496-eba91bd3e84b"],
        "notes": "Adjudicated to Robbins Basis 11th p.584-586 covering JAK2 V617F constitutive kinase activation in Polycythemia Vera."
    },
    "hem-010": {
        "expected_chunks": ["acbda90f-b0cd-5fd5-8f15-5fd182f90a63", "37a3bb16-aff1-59c6-98ed-5ca709063a33", "4968079c-8b13-5a50-8207-8d622bdcec83"],
        "notes": "Adjudicated to Robbins Basis 11th p.608, p.611 and Robbins Review p.224 covering megaloblastic anemia lab findings and bone marrow morphology."
    },
    "neop-006": {
        "expected_chunks": ["f7556cfb-a1e3-5637-afff-672ee4add8cc", "c12f0585-a01b-5ed4-8660-7565ea1c93a5", "ba2f6964-c24d-557f-8cc8-a7d03a7acfd5"],
        "notes": "Adjudicated to Robbins Basis 11th p.759, p.298 covering DNA mismatch repair deficiency and microsatellite instability (MSI)."
    },
    "neop-008": {
        "expected_chunks": ["b4ea1130-d6fc-5e94-9c90-45a0aea44a68", "74be41a6-f31d-506e-b11b-2e79836811e3", "75b873ca-dfda-5067-86ff-137b00b45e1f"],
        "notes": "Adjudicated to Robbins Basis 11th p.256, p.311-312 covering histologic grade and degree of differentiation/anaplasia."
    },
    "neop-010": {
        "expected_chunks": ["91843dcc-ce60-5ada-88e8-4810692eff0a", "5f4b956e-4cb6-5874-b033-126de022db1b", "c7b4068a-2082-5dff-9cb4-2c0bc814b31c"],
        "notes": "Adjudicated to Robbins Basis 11th p.306 and Robbins Review p.97 covering HPV E6 targeting p53 and E7 targeting RB."
    },
    "sys-001": {
        "expected_chunks": ["c5db27a0-a790-50f2-aed4-e08874c7653b", "7d63bd7f-758b-512d-9e15-00d5a8767d45", "763ba3a0-7e81-52ba-ae8a-a56df0911e01"],
        "notes": "Adjudicated to Robbins Basis 11th p.845 and Sternberg Review 2nd p.838, p.857 covering minimal change disease LM vs EM podocyte effacement."
    },
    "sys-004": {
        "expected_chunks": ["aac6badb-1305-5ee5-a034-a33fc51e71ef", "da4d7505-5dfd-5898-8664-e736165d07a6", "96ebcf61-4970-5b9e-8d34-37f5eb654f22"],
        "notes": "Adjudicated to Robbins Basis 11th p.644 and Sternberg Review 2nd p.552, p.564 covering UIP / IPF diagnostic criteria."
    },
    "sys-005": {
        "expected_chunks": ["5c8c6889-b359-52c3-9d7b-539f9b2b0455", "b55e8199-e98b-5b43-bad0-9f910c8aeb4d", "80256606-c5a9-5e4f-a1fd-424eedd3e066"],
        "notes": "Adjudicated to Robbins Basis 11th p.511, p.513, p.514 covering gross and microscopic evolutionary stages of acute myocardial infarction."
    },
    "sys-008": {
        "expected_chunks": ["0ecc2959-aa98-5c6b-ad9a-8c3c6e62bd04", "2f66ea80-e423-58e6-9f23-f0e7e1258ef1", "f84c079c-0402-580b-89a8-635e0d666f22"],
        "notes": "Adjudicated to Robbins Basis 11th p.842-843 Fig 20.9 covering crescentic glomerulonephritis morphology and clinical course."
    },
}

def main():
    slug = "m16a-retrieval-v1"
    reviewer_id = "5879bbe4-268c-4f7b-8ffb-ea4a8811396d"

    with sessionmaker(bind=engine)() as session:
        benchmark = session.query(RetrievalBenchmark).filter_by(slug=slug).first()
        if not benchmark:
            raise ValueError(f"Benchmark not found: {slug}")
        
        print(f"Applying adjudications to benchmark: {slug}...")
        for case_key, adj in ADJUDICATIONS.items():
            case = session.query(RetrievalBenchmarkCase).filter_by(
                benchmark_id=benchmark.id, case_key=case_key
            ).first()
            if not case:
                print(f"Warning: Case {case_key} not found")
                continue
            
            # Step 1: Save draft with updated evidence and notes
            updated = RetrievalReviewService.update_case(
                session,
                slug=slug,
                case_id=case.id,
                reviewer_id=reviewer_id,
                expected_revision=case.revision,
                domain=case.domain,
                query=case.query,
                expected_chunk_ids=adj["expected_chunks"],
                out_of_corpus=case.out_of_corpus,
                notes=adj["notes"],
            )
            
            # Step 2: Approve and verify
            verified = RetrievalReviewService.decide_case(
                session,
                slug=slug,
                case_id=case.id,
                reviewer_id=reviewer_id,
                expected_revision=updated["revision"],
                approve=True,
                notes=adj["notes"],
            )
            print(f"  [OK] {case_key} -> Rev {verified['revision']} (Status: {verified['verification_status']}) with {len(adj['expected_chunks'])} chunks")

    engine.dispose()
    print("\nAll 19 adjudications successfully applied to PostgreSQL!")

if __name__ == "__main__":
    main()
