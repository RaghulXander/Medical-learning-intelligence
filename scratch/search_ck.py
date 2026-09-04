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

with sessionmaker(bind=engine)() as session:
    chunks = session.query(DocumentChunk, SourceDocument, Source).join(
        SourceDocument, DocumentChunk.document_id == SourceDocument.id
    ).join(Source, SourceDocument.source_id == Source.id).filter(
        DocumentChunk.content.ilike("%cytokeratin 7%") | DocumentChunk.content.ilike("%CK7%")
    ).filter(
        DocumentChunk.content.ilike("%cytokeratin 20%") | DocumentChunk.content.ilike("%CK20%")
    ).all()
    
    print(f"Found {len(chunks)} chunks for CK7 + CK20:")
    for ch, doc, src in chunks:
        print(f"  Chunk ID: '{ch.id}' | {src.short_name} p.{ch.pdf_page}")
        print(f"    Preview: {ch.content[:200]}...\n")

engine.dispose()
