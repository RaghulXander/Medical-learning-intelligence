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

from database.models import Question, QuestionEvidence, SourceDocument, Source

with sessionmaker(bind=engine)() as session:
    pilot_questions = session.query(Question).filter(
        Question.status.in_(["HUMAN_REVIEW", "AI_REVIEW", "GENERATED"])
    ).order_by(Question.created_at.desc()).limit(50).all()
    
    print(f"Retrieved {len(pilot_questions)} pilot candidates from database:")
    status_counts = {}
    domain_counts = {}
    difficulty_counts = {}
    
    for q in pilot_questions:
        status_counts[q.status] = status_counts.get(q.status, 0) + 1
        domain_counts[q.speciality] = domain_counts.get(q.speciality, 0) + 1
        difficulty_counts[q.difficulty] = difficulty_counts.get(q.difficulty, 0) + 1
        
    print("Status Breakdown:", status_counts)
    print("Domain Breakdown:", domain_counts)
    print("Difficulty Breakdown:", difficulty_counts)
    
    # Check evidence linkage
    for q in pilot_questions[:5]:
        evidence_count = session.query(QuestionEvidence).filter_by(question_id=q.id).count()
        print(f"\n[Question {q.id}] ({q.status}) Score: {q.quality_score}")
        print(f"Stem: {q.stem[:120]}...")
        print(f"Correct Option: {q.correct_option}")
        print(f"Evidence rows attached: {evidence_count}")

engine.dispose()
