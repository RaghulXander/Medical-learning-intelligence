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
    # check diag-006 chunk ids
    for cid in ['26535c44-582a-5758-b1f1-2b54026a29b6', 'ec693a74-984a-592b-abfa-35222ef45b7a']:
        ch = session.query(DocumentChunk, SourceDocument, Source).join(
            SourceDocument, DocumentChunk.document_id == SourceDocument.id
        ).join(Source, SourceDocument.source_id == Source.id).filter(DocumentChunk.id == cid).first()
        print(f"ID {cid} -> {ch[2].short_name if ch else 'NOT FOUND'}")
        
    # Search for ALL flow cytometry immunophenotype chunks
    chunks = session.query(DocumentChunk, SourceDocument, Source).join(
        SourceDocument, DocumentChunk.document_id == SourceDocument.id
    ).join(Source, SourceDocument.source_id == Source.id).filter(
        DocumentChunk.content.ilike("%lymphoblastic leukemia%") | DocumentChunk.content.ilike("%B-ALL%")
    ).filter(
        DocumentChunk.content.ilike("%flow cytometry%") | DocumentChunk.content.ilike("%immunophenotype%")
    ).all()
    print(f"\nFound {len(chunks)} chunks for B-ALL/T-ALL immunophenotype:")
    for ch, doc, src in chunks[:5]:
        print(f"  Chunk ID: '{ch.id}' | {src.short_name} p.{ch.pdf_page}")
        print(f"    Preview: {ch.content[:180]}...\n")

engine.dispose()
