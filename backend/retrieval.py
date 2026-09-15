"""Retrieval interface: replace implementation later without changing API/UI shapes."""
import re
from typing import Protocol
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.models import Document, DocumentChunk


def chunks(segments, size=1200, overlap=180):
    """Prefer paragraph/sentence/word boundaries; never cross source locations."""
    position = 0
    for segment in segments:
        value = segment["text"]
        start = 0
        while start < len(value):
            end = min(start + size, len(value))
            if end < len(value):
                for boundary in ("\n\n", ". ", "\n", " "):
                    cut = value.rfind(boundary, start + size // 2, end)
                    if cut > start:
                        end = cut + len(boundary)
                        break
            passage = value[start:end].strip()
            if passage:
                position += 1
                yield {"position": position, "text": passage, "page": segment["page"], "section": segment["section"]}
            if end == len(value):
                break
            next_start = max(start + 1, end - overlap)
            # Avoid splitting the first overlapping word.
            while next_start < end and not value[next_start - 1].isspace():
                next_start += 1
            start = next_start


def location(page, section, position):
    return f"Page {page}" if page else f"Section: {section}" if section else f"Passage {position}"


class PassageRetriever(Protocol):
    def search(self, session: Session, query: str, limit: int, document_id: str | None = None) -> dict: ...


class SQLiteRetriever:
    def __init__(self, force_keyword=False):
        self.force_keyword = force_keyword

    def search(self, session, query, limit=20, document_id=None):
        has_fts = not self.force_keyword and session.scalar(text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='document_fts'")) > 0
        mode = "fts5" if has_fts else "keyword"
        tokens = list(dict.fromkeys(re.findall(r"[^\W_]+", query, re.UNICODE)))[:16]
        if not tokens:
            return {"query": query, "mode": mode, "results": [], "message": "Enter a word or phrase to search your documents."}
        if has_fts:
            # User text is tokenized and quoted. Operators and SQL are never executed.
            match = " AND ".join('"' + token + '"' for token in tokens)
            rows = session.execute(text("""SELECT c.id, c.document_id, c.position, c.page, c.section, c.text, d.title
                FROM document_fts JOIN document_chunks c ON c.id = document_fts.rowid
                JOIN documents d ON d.id = c.document_id
                WHERE document_fts MATCH :query AND d.status = 'ready'
                AND (:document_id IS NULL OR d.id = :document_id)
                ORDER BY bm25(document_fts), c.id LIMIT :limit"""), {"query": match, "document_id": document_id, "limit": limit}).mappings().all()
        else:
            statement = select(DocumentChunk.id, DocumentChunk.document_id, DocumentChunk.position, DocumentChunk.page, DocumentChunk.section, DocumentChunk.text, Document.title).join(Document).where(Document.status == "ready")
            for token in tokens:
                statement = statement.where(DocumentChunk.text.icontains(token, autoescape=True))
            if document_id:
                statement = statement.where(Document.id == document_id)
            rows = session.execute(statement.order_by(DocumentChunk.id).limit(limit)).mappings().all()
        return {"query": query, "mode": mode, "results": [{**row, "location": location(row["page"], row["section"], row["position"])} for row in rows], "message": f"Showing up to {limit} matching passages." if rows else "No matching passages. Try other words or upload a relevant document."}
