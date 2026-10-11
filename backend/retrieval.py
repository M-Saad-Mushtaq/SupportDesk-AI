"""Retrieval interface: replace implementation later without changing API/UI shapes."""
import json
import re
from typing import Protocol
from sqlalchemy import or_, select, text
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


# Common English words that carry no search meaning. Dropped from partial
# matching so "how do I return an item" does not match every passage with "I".
STOPWORDS = frozenset("""a an and are as at be but by can could do does did for from had has have how i if in into is it its
me my no not of on or our please should so than that the their them then there these they this to us was we were what
when where which who why will with would you your""".split())


def query_terms(query):
    """Lower-cased word tokens only: punctuation, quotes and FTS operators are discarded, never executed."""
    return list(dict.fromkeys(token.lower() for token in re.findall(r"[^\W_]+", query, re.UNICODE)))[:16]


def useful_terms(tokens):
    useful = [token for token in tokens if token not in STOPWORDS and (len(token) > 1 or token.isdigit())]
    return useful or tokens


def required_matches(terms):
    # Long questions may include words absent from every policy; still require
    # more than one shared term so a single incidental word is not "evidence".
    return 1 if len(terms) < 4 else 2


def keyword_stem(token):
    """Light suffix stripping for the no-FTS5 fallback (substring matching):
    returning/returned/returns -> return. FTS5 itself uses the Porter stemmer."""
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[:-len(suffix)]
    return token


def fts_phrase(token):
    return '"' + token.replace('"', '""') + '"'


class SQLiteRetriever:
    """Local keyword search. FTS5 uses the Porter stemmer (migration d5f0c7a9e214),
    so return/returns/returned share one index term. Strict all-terms matching is
    tried first; if it finds nothing, ranked partial matching is used. This is
    still keyword retrieval, not semantic search."""

    def __init__(self, force_keyword=False):
        self.force_keyword = force_keyword

    def search(self, session, query, limit=20, document_id=None):
        has_fts = not self.force_keyword and session.scalar(text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='document_fts'")) > 0
        mode = "fts5" if has_fts else "keyword"
        tokens = query_terms(query)
        if not tokens:
            return {"query": query, "mode": mode, "match": "none", "results": [], "message": "Enter a word or phrase to search your documents."}
        search = self._fts if has_fts else self._keyword
        rows, match = search(session, tokens, limit, document_id), "all_terms"
        if not rows:
            rows, match = search(session, useful_terms(tokens), limit, document_id, partial=True), "partial_terms"
        if not rows:
            match = "none"
        message = (f"Showing up to {limit} passages containing every search word." if match == "all_terms"
                   else f"No passage contains every search word. Showing up to {limit} passages ranked by how many search words they share." if match == "partial_terms"
                   else "No matching passages. Try other words or upload a relevant document.")
        return {"query": query, "mode": mode, "match": match, "results": [{**row, "location": location(row["page"], row["section"], row["position"])} for row in rows], "message": message}

    def _fts(self, session, terms, limit, document_id, partial=False):
        # Every term is a quoted FTS string bound as a parameter; user text never
        # becomes FTS operators or SQL. The table tokenizer stems quoted terms too.
        base = """SELECT c.id, c.document_id, c.position, c.page, c.section, c.text, d.title, bm25(document_fts) AS score
            FROM document_fts JOIN document_chunks c ON c.id = document_fts.rowid
            JOIN documents d ON d.id = c.document_id
            WHERE document_fts MATCH :query AND d.status = 'ready'
            AND (:document_id IS NULL OR d.id = :document_id)"""
        strip = lambda rows: [{key: row[key] for key in row.keys() if key != "score"} for row in rows]
        if not partial:
            return strip(session.execute(text(base + " ORDER BY score, c.id LIMIT :limit"), {"query": " AND ".join(map(fts_phrase, terms)), "document_id": document_id, "limit": limit}).mappings().all())
        candidates = session.execute(text(base + " ORDER BY score, c.id LIMIT 200"), {"query": " OR ".join(map(fts_phrase, terms)), "document_id": document_id}).mappings().all()
        if not candidates:
            return []
        # Count distinct matched (stemmed) terms per passage using FTS itself.
        ids = [row["id"] for row in candidates]
        matched = dict.fromkeys(ids, 0)
        for term in terms:
            for row_id in session.execute(text("SELECT rowid FROM document_fts WHERE document_fts MATCH :term AND rowid IN (SELECT value FROM json_each(:ids))"), {"term": fts_phrase(term), "ids": json.dumps(ids)}).scalars():
                matched[row_id] += 1
        needed = required_matches(terms)
        ranked = sorted((row for row in candidates if matched[row["id"]] >= needed), key=lambda row: (-matched[row["id"]], row["score"], row["id"]))
        return strip(ranked[:limit])

    def _keyword(self, session, terms, limit, document_id, partial=False):
        # Fallback when SQLite lacks FTS5: parameterized, escaped substring
        # matching on lightly stemmed terms.
        terms = list(dict.fromkeys(map(keyword_stem, terms)))
        statement = select(DocumentChunk.id, DocumentChunk.document_id, DocumentChunk.position, DocumentChunk.page, DocumentChunk.section, DocumentChunk.text, Document.title).join(Document).where(Document.status == "ready")
        if document_id:
            statement = statement.where(Document.id == document_id)
        if not partial:
            for term in terms:
                statement = statement.where(DocumentChunk.text.icontains(term, autoescape=True))
            return [dict(row) for row in session.execute(statement.order_by(DocumentChunk.id).limit(limit)).mappings()]
        statement = statement.where(or_(*(DocumentChunk.text.icontains(term, autoescape=True) for term in terms)))
        rows = [dict(row) for row in session.execute(statement.order_by(DocumentChunk.id).limit(500)).mappings()]
        count = lambda row: sum(term in row["text"].lower() for term in terms)
        return sorted((row for row in rows if count(row) >= required_matches(terms)), key=lambda row: (-count(row), row["id"]))[:limit]
