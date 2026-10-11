"""Knowledge Base routes: real local documents, no generated answers."""
from typing import Annotated, Literal
from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.documents import delete_document, document_out, get_document, recover_documents, upload_document
from backend.models import Document
from backend.retrieval import PassageRetriever, SQLiteRetriever

DocumentStatus = Literal["processing", "ready", "needs_ocr", "failed", "deleting"]


class SegmentOut(BaseModel):
    text: str
    page: int | None
    section: str | None


class DocumentOut(BaseModel):
    id: str
    title: str
    filename: str
    format: str
    size: int
    content_hash: str
    status: DocumentStatus
    error: str | None
    warning: str | None
    created_at: str
    updated_at: str
    page_count: int
    chunk_count: int


class PreviewOut(DocumentOut):
    segments: list[SegmentOut]


class UploadOut(BaseModel):
    document: DocumentOut
    duplicate: bool


class SearchHit(SegmentOut):
    id: int
    document_id: str
    position: int
    title: str
    location: str


class SearchOut(BaseModel):
    query: str
    mode: Literal["fts5", "keyword"]
    match: Literal["all_terms", "partial_terms", "none"]
    results: list[SearchHit]
    message: str


def document_router(engine, root, retriever: PassageRetriever | None = None):
    router = APIRouter(prefix="/api/documents", tags=["Knowledge Base"], responses={404: {"description": "Document not found."}, 409: {"description": "Document is processing or deletion is pending."}, 413: {"description": "File exceeds 10 MB."}, 415: {"description": "Unsupported file extension/content type or invalid PDF header."}, 422: {"description": "Invalid request or missing file."}, 503: {"description": "Database or local storage unavailable. Retry after correcting the reported problem."}})
    retrieval = retriever or SQLiteRetriever()

    @router.post("", response_model=UploadOut)
    def upload(file: Annotated[UploadFile, File(description="One text-based PDF, UTF-8 TXT, or Markdown file. Maximum 10 MB. UTF-16 text with a BOM is also accepted.")]):
        """Store and extract locally. Same content hash returns the existing document without duplication. Inspect the returned processing status: failed/needs_ocr is not a successful extraction. No OCR. Processing runs up to 30 seconds; PDF limits: 200 pages and 2 million extracted characters. Delete failed records before retrying the same file."""
        recover_documents(engine, root)
        return upload_document(engine, root, file)

    @router.get("", response_model=list[DocumentOut])
    def documents(q: Annotated[str, Query(max_length=200)] = "", status: DocumentStatus | None = None):
        """List metadata; filter title/filename and processing status. Stale processing jobs become failed after 90 seconds on a document read or restart; interrupted deletions are retried."""
        recover_documents(engine, root)
        with Session(engine) as session:
            statement = select(Document)
            if status:
                statement = statement.where(Document.status == status)
            if q.strip():
                statement = statement.where(Document.filename.icontains(q.strip(), autoescape=True))
            return [document_out(session, doc) for doc in session.scalars(statement.order_by(Document.created_at.desc(), Document.id))]

    @router.get("/search", response_model=SearchOut)
    def search(q: Annotated[str, Query(max_length=200)] = "", limit: Annotated[int, Query(ge=1, le=50)] = 20, document_id: str | None = None):
        """Document search (keyword), not semantic search. Up to 16 distinct word tokens. FTS5 uses Porter stemming (return/returns/returned match). Passages containing every word are returned first (match=all_terms); if none exist, passages sharing the most non-stopword terms are ranked (match=partial_terms; long questions need 2+ shared terms). User FTS operators and punctuation are never accepted as syntax. Returns up to limit passages with source locations, never AI answers or confidence scores. Empty/no-match queries return clear messages. FTS5 when available; otherwise escaped keyword substring matching."""
        with Session(engine) as session:
            return retrieval.search(session, q, limit, document_id)

    @router.get("/{document_id}", response_model=PreviewOut)
    def preview(document_id: str):
        """Preview extracted plain text, preserving PDF pages and Markdown headings. Original files are never publicly served. HTML/Markdown is returned as text, not executable content."""
        recover_documents(engine, root)
        with Session(engine) as session:
            return document_out(session, get_document(session, document_id), preview=True)

    @router.delete("/{document_id}")
    def remove(document_id: str):
        """Call only after user confirmation. Removes the stored file, chunks, FTS entries and metadata. Repeated deletion is safe. Interrupted/failed file deletion stays marked deleting and can be retried; success is returned only after cleanup."""
        recover_documents(engine, root)
        return delete_document(engine, root, document_id)

    return router
