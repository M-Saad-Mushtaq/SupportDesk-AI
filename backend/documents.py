"""Local file lifecycle and SQLite document metadata. No public file serving."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.orm import Session

from backend.database import write_session
from backend.models import Document, DocumentChunk
from backend.retrieval import chunks
from backend.service import now

MAX_UPLOAD = 10 * 1024 * 1024
PROCESS_TIMEOUT = 30
STALE_SECONDS = 90
ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def storage_root(folder=None):
    path = Path(folder or os.environ.get("UPLOAD_DIR", ROOT / "backend" / "uploads")).resolve()
    if path == ROOT / "frontend" or (ROOT / "frontend") in path.parents:
        raise ValueError("UPLOAD_DIR must be outside the frontend directory.")
    return path


def stored_path(root, name):
    if not re.fullmatch(r"[0-9a-f]{32}\.(pdf|txt|md)", name):
        raise HTTPException(409, "Invalid stored filename. No file was accessed.")
    path = (root / name).resolve()
    if path.parent != root.resolve():
        raise HTTPException(409, "Stored file is outside the upload folder. No file was accessed.")
    return path


def document_out(session, document, preview=False):
    value = {key: getattr(document, key) for key in ("id", "title", "filename", "format", "size", "content_hash", "status", "error", "warning", "created_at", "updated_at", "page_count")}
    value["chunk_count"] = session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document.id))
    if preview:
        value["segments"] = document.segments
    return value


def get_document(session, document_id):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found. Refresh the document list.")
    return doc


def run_extraction(path):
    try:
        result = subprocess.run([sys.executable, "-m", "backend.extraction", str(path)], cwd=ROOT, capture_output=True, timeout=PROCESS_TIMEOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode != 0:
            raise ValueError("Extraction process stopped")
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        message = "Extraction exceeded 30 seconds. Split or simplify the document and upload again."
    except (ValueError, OSError):
        message = "The local text extractor could not finish. Check local storage and upload a text-based copy."
    return {"status": "failed", "error": message, "warning": None, "segments": [], "page_count": 0}


def upload_document(engine, root, file):
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    suffix = Path(filename).suffix.lower()
    if not filename or len(filename) > 240 or any(ord(c) < 32 for c in filename):
        raise HTTPException(422, "Choose a filename of 1-240 characters without control characters.")
    mime_types = {".pdf": {"application/pdf"}, ".txt": {"text/plain"}, ".md": {"text/markdown", "text/plain", "text/x-markdown"}}
    if suffix not in mime_types or (file.content_type and file.content_type.split(';')[0] not in mime_types[suffix] | {"application/octet-stream"}):
        raise HTTPException(415, "Supported files: text-based PDF, TXT, or Markdown (.md).")
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "The file exceeds the 10 MB limit. Split it and retry.")
    if suffix == ".pdf" and data and not data.startswith(b"%PDF-"):
        raise HTTPException(415, "The selected .pdf file does not have a PDF header.")
    digest = hashlib.sha256(data).hexdigest()
    with write_session(engine) as session:
        existing = session.scalar(select(Document).where(Document.content_hash == digest))
        if existing:
            if existing.status == "deleting":
                raise HTTPException(409, "This document is being deleted. Retry deletion before uploading it again.")
            return {"document": document_out(session, existing), "duplicate": True}
        doc = Document(id=str(uuid4()), title=Path(filename).stem, filename=filename, storage_name=uuid4().hex + suffix, format=suffix[1:].upper(), size=len(data), content_hash=digest, status="processing", error=None, warning=None, created_at=now(), updated_at=now(), page_count=0, segments=[])
        session.add(doc)
        session.commit()
        document_id, name = doc.id, doc.storage_name
    path = stored_path(root, name)
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        root.mkdir(parents=True, exist_ok=True)
        with temporary.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
        result = run_extraction(path)
    except OSError:
        result = {"status": "failed", "error": "The file could not be stored locally. Check folder permissions and available disk space, then delete this failed record and retry.", "warning": None, "segments": [], "page_count": 0}
    with write_session(engine) as session:
        doc = get_document(session, document_id)
        if doc.status == "processing":
            for key in ("status", "error", "warning", "segments", "page_count"):
                setattr(doc, key, result[key])
            doc.updated_at = now()
            if doc.status == "ready":
                session.add_all(DocumentChunk(document_id=doc.id, **chunk) for chunk in chunks(doc.segments))
            session.flush()
            session.commit()
        return {"document": document_out(session, doc), "duplicate": False}


def finish_delete(engine, root, document_id):
    failure = None
    with write_session(engine) as session:
        doc = session.get(Document, document_id)
        if not doc:
            return
        if doc.status != "deleting":
            return
        path = stored_path(root, doc.storage_name)
        try:
            path.unlink(missing_ok=True)
            path.with_suffix(path.suffix + ".part").unlink(missing_ok=True)
        except OSError:
            failure = "Could not remove the stored file. Close programs using it, check folder permissions, and retry Delete."
            doc.error = failure
            session.commit()
        else:
            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            session.delete(doc)
            session.commit()
    if failure:
        raise HTTPException(503, failure)


def delete_document(engine, root, document_id):
    with write_session(engine) as session:
        doc = session.get(Document, document_id)
        if not doc:
            return {"deleted": True}  # Idempotent, including lost-response retries.
        if doc.status == "processing":
            raise HTTPException(409, "Document is processing. Wait briefly and refresh before deleting.")
        doc.status = "deleting"
        doc.updated_at = now()
        session.commit()
    finish_delete(engine, root, document_id)
    return {"deleted": True}


def recover_documents(engine, root):
    """Bound stale jobs; finish interrupted deletions on startup or document reads."""
    if not inspect(engine).has_table("documents"):
        return  # Keep health and unmigrated setup behavior working.
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)).isoformat()
    with write_session(engine) as session:
        for doc in session.scalars(select(Document).where(Document.status == "processing", Document.updated_at < cutoff)):
            doc.status = "failed"
            doc.error = "Processing was interrupted. Delete this record and upload the document again."
            doc.updated_at = now()
        deleting = list(session.scalars(select(Document.id).where(Document.status == "deleting")))
        session.commit()
    for document_id in deleting:
        try:
            finish_delete(engine, root, document_id)
        except (HTTPException, OSError):
            logger.warning("Document deletion still needs retry: %s", document_id)
