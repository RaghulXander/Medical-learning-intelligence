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

from database.models import RetrievalBenchmarkCase

with sessionmaker(bind=engine)() as session:
    c = session.query(RetrievalBenchmarkCase).filter(RetrievalBenchmarkCase.reviewer_id.isnot(None)).first()
    print("Existing reviewer_id:", c.reviewer_id if c else "None")

engine.dispose()
