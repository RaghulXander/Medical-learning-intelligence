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

from database.models import DocumentChunk, SourceDocument, Source
from scripts.apply_m19c_gold_adjudication import ADJUDICATIONS

# Update diag-006 chunk
ADJUDICATIONS["diag-006"]["expected_chunks"] = [
    "26535c44-582a-5758-b1f1-2b54026a29b6",
    "1ecbc0a4-688d-5f5a-b105-957b4696f4b4",
    "de948f45-fc91-5783-9094-1d2d3b5de298"
]

all_cids = set()
for k, v in ADJUDICATIONS.items():
    all_cids.update(v["expected_chunks"])

with sessionmaker(bind=engine)() as session:
    found = session.query(DocumentChunk.id, Source.short_name, DocumentChunk.pdf_page).join(
        SourceDocument, DocumentChunk.document_id == SourceDocument.id
    ).join(Source, SourceDocument.source_id == Source.id).filter(
        DocumentChunk.id.in_(all_cids)
    ).all()
    
    found_dict = {f[0]: f for f in found}
    print(f"Validated {len(found)} / {len(all_cids)} chunk IDs in DB.")
    missing = all_cids - set(found_dict.keys())
    if missing:
        print("MISSING CHUNK IDS:", missing)
    else:
        print("ALL CHUNK IDS ARE 100% VALID IN THE DATABASE!")

engine.dispose()
