from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject, NumberObject
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.database import make_engine, write_session
from backend.main import create_app
from backend.models import Document, DocumentChunk
from backend.documents import MAX_UPLOAD, stored_path
from backend.retrieval import SQLiteRetriever, chunks
from backend.tests.test_api import migrate


@pytest.fixture
def library(tmp_path):
    url = f"sqlite:///{tmp_path / 'documents.db'}"
    migrate(url)
    engine = make_engine(url)
    folder = tmp_path / "uploads"
    with TestClient(create_app(engine, folder)) as client:
        yield client, engine, folder, url


def upload(client, name="guide.txt", data=b"Shipping delivery takes five business days.", mime="text/plain"):
    return client.post("/api/documents", files={"file": (name, data, mime)})


def pdf(pages):
    writer = PdfWriter()
    for value in pages:
        page = writer.add_blank_page(width=612, height=792)
        if value is not None:
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(b"BT /F1 12 Tf 50 700 Td (" + value.encode("ascii") + b") Tj ET")
        else:
            # A real image-only page; extraction must not invent any text.
            image = DecodedStreamObject()
            image.set_data(b"\xff\xff\xff")
            image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"), NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1), NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Img"): writer._add_object(image)})})
            stream = DecodedStreamObject()
            stream.set_data(b"q 100 0 0 100 0 0 cm /Img Do Q")
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_real_text_upload_generated_path_filters_and_duplicate(library):
    client, engine, folder, _ = library
    result = upload(client, "../../outside.txt")
    assert result.status_code == 200
    doc = result.json()["document"]
    assert doc["status"] == "ready" and doc["filename"] == "outside.txt"
    assert doc["chunk_count"] == 1
    files = list(folder.iterdir())
    assert len(files) == 1 and files[0].name != "outside.txt"
    assert files[0].parent == folder and files[0].read_bytes().startswith(b"Shipping")
    assert not (folder.parent / "outside.txt").exists()
    duplicate = upload(client, "another-title.txt").json()
    assert duplicate["duplicate"] and duplicate["document"]["id"] == doc["id"]
    assert len(list(folder.iterdir())) == 1
    assert client.get("/api/documents", params={"q": "outside", "status": "ready"}).json()[0]["id"] == doc["id"]
    assert client.get("/api/documents", params={"q": "%"}).json() == []
    assert client.get("/api/documents", params={"status": "bogus"}).status_code == 422
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Document)) == 1
    with pytest.raises(Exception):
        stored_path(folder, "../../outside.txt")


def test_concurrent_duplicate_uploads(library):
    client, _, folder, _ = library
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: upload(client).json(), range(2)))
    assert results[0]["document"]["id"] == results[1]["document"]["id"]
    assert sum(not result["duplicate"] for result in results) == 1
    assert len(list(folder.iterdir())) == 1
    assert len(client.get("/api/documents").json()) == 1


@pytest.mark.parametrize("name,data,mime,code", [
    ("script.exe", b"text", "application/octet-stream", 415),
    ("image.txt", b"image", "image/png", 415),
    ("fake.pdf", b"not a pdf", "application/pdf", 415),
    ("huge.txt", b"x" * (MAX_UPLOAD + 1), "text/plain", 413),
], ids=["unsupported-extension", "wrong-content-type", "invalid-pdf-header", "over-10mb"])
def test_invalid_uploads_are_rejected_without_records(library, name, data, mime, code):
    client, _, folder, _ = library
    assert upload(client, name, data, mime).status_code == code
    assert client.get("/api/documents").json() == []
    assert not folder.exists()


@pytest.mark.parametrize("name,data,mime,expected", [
    ("empty.txt", b"   ", "text/plain", "failed"),
    ("binary.txt", b"\x00\x01binary", "text/plain", "failed"),
    ("empty.pdf", pdf([]), "application/pdf", "failed"),
    ("scanned.pdf", pdf([None]), "application/pdf", "needs_ocr"),
    ("broken.pdf", b"%PDF-broken", "application/pdf", "failed"),
], ids=["empty-text", "binary-text", "zero-page-pdf", "scanned-pdf", "corrupt-pdf"])
def test_failed_and_scanned_files_never_appear_ready(library, name, data, mime, expected):
    client, _, _, _ = library
    response = upload(client, name, data, mime)
    assert response.status_code == 200
    doc = response.json()["document"]
    assert doc["status"] == expected and doc["error"] and doc["chunk_count"] == 0
    if expected == "needs_ocr":
        assert "OCR" in doc["error"]
    assert client.get("/api/documents/search", params={"q": "text"}).json()["results"] == []
    assert client.delete('/api/documents/' + doc['id']).json() == {"deleted": True}


def test_pdf_pages_and_markdown_sections_in_search_and_preview(library):
    client, _, _, _ = library
    pdf_doc = upload(client, "policy.pdf", pdf(["Shipping takes five days.", "Refund window lasts thirty days.", None]), "application/pdf").json()["document"]
    assert pdf_doc["status"] == "ready" and pdf_doc["page_count"] == 3
    assert "3" in pdf_doc["warning"]
    found = client.get("/api/documents/search", params={"q": "refund window"}).json()
    assert found["mode"] == "fts5" and len(found["results"]) == 1
    assert found["results"][0]["page"] == 2 and found["results"][0]["location"] == "Page 2"
    preview = client.get('/api/documents/' + pdf_doc['id']).json()
    assert [segment["page"] for segment in preview["segments"]] == [1, 2]
    markdown = b"# Delivery\nPackages arrive on weekdays.\n\n## Returns\nContact support for a return label."
    md = upload(client, "help.md", markdown, "text/markdown").json()["document"]
    hit = client.get("/api/documents/search", params={"q": "return label", "document_id": md["id"]}).json()["results"][0]
    assert hit["section"] == "Returns" and hit["location"] == "Section: Returns"
    assert hit["title"] == "help" and "Contact support" in hit["text"]
    utf16 = upload(client, "unicode.txt", "International delivery information".encode("utf-16")).json()["document"]
    assert utf16["status"] == "ready"


def test_search_empty_no_matches_operator_safety_and_keyword_fallback(library):
    client, engine, _, _ = library
    doc = upload(client).json()["document"]
    for query in ("", "  ", "*()"):
        found = client.get("/api/documents/search", params={"q": query}).json()
        assert not found["results"] and "Enter" in found["message"]
    for query in ("unfindable", '" OR * - NEAR(', "'; DROP TABLE documents; --"):
        response = client.get("/api/documents/search", params={"q": query})
        assert response.status_code == 200 and not response.json()["results"]
    assert len(client.get("/api/documents").json()) == 1
    with Session(engine) as session:
        fallback = SQLiteRetriever(force_keyword=True).search(session, "shipping delivery")
        assert fallback["mode"] == "keyword" and fallback["results"][0]["document_id"] == doc["id"]
    # Also exercise a migrated database without the optional FTS objects.
    with engine.begin() as connection:
        for trigger in ("document_chunks_ai", "document_chunks_ad", "document_chunks_au"):
            connection.exec_driver_sql(f"DROP TRIGGER {trigger}")
        connection.exec_driver_sql("DROP TABLE document_fts")
    assert client.get("/api/documents/search", params={"q": "shipping"}).json()["mode"] == "keyword"


def test_chunks_overlap_without_losing_source_boundaries():
    value = "Delivery and return policy details. " * 150
    parts = list(chunks([{"text": value, "page": 4, "section": None}]))
    assert len(parts) > 1
    assert all(part["page"] == 4 and 0 < len(part["text"]) <= 1200 for part in parts)
    assert parts[0]["text"][-100:] in parts[1]["text"]
    assert [part["position"] for part in parts] == list(range(1, len(parts) + 1))


def test_restart_persistence_and_complete_idempotent_deletion(library):
    client, engine, folder, url = library
    doc = upload(client).json()["document"]
    with TestClient(create_app(make_engine(url), folder)) as restarted:
        assert restarted.get('/api/documents/' + doc['id']).json()["segments"]
        assert len(list(folder.iterdir())) == 1
        assert restarted.get("/api/documents/search", params={"q": "delivery"}).json()["results"]
        assert restarted.delete('/api/documents/' + doc['id']).json() == {"deleted": True}
        assert restarted.delete('/api/documents/' + doc['id']).json() == {"deleted": True}
        assert restarted.get('/api/documents/' + doc['id']).status_code == 404
        assert not restarted.get("/api/documents/search", params={"q": "delivery"}).json()["results"]
    assert list(folder.iterdir()) == []
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(DocumentChunk)) == 0
        assert session.scalar(text("SELECT count(*) FROM document_fts WHERE document_fts MATCH 'delivery'")) == 0


def test_extraction_timeout_and_interrupted_processing_recovery(library, monkeypatch):
    client, engine, folder, url = library
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 30)
    with monkeypatch.context() as patch:
        patch.setattr("backend.documents.subprocess.run", timeout)
        doc = upload(client).json()["document"]
        assert doc["status"] == "failed" and "30 seconds" in doc["error"]
    with write_session(engine) as session:
        record = session.get(Document, doc["id"])
        record.status = "processing"
        record.updated_at = "2020-01-01T00:00:00+00:00"
        session.commit()
    with TestClient(create_app(make_engine(url), folder)) as restarted:
        recovered = restarted.get('/api/documents/' + doc['id']).json()
        assert recovered["status"] == "failed" and "interrupted" in recovered["error"]
        assert restarted.delete('/api/documents/' + doc['id']).status_code == 200


def test_failed_file_deletion_is_recoverable(library, monkeypatch):
    client, engine, folder, url = library
    doc = upload(client).json()["document"]
    original_unlink = Path.unlink
    def locked(path, *args, **kwargs):
        if path.parent == folder:
            raise PermissionError("File locked")
        return original_unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", locked)
        response = client.delete('/api/documents/' + doc['id'])
        assert response.status_code == 503 and "retry" in response.json()["detail"]
        with Session(engine) as session:
            assert session.get(Document, doc["id"]).status == "deleting"
        assert client.get("/api/documents/search", params={"q": "shipping"}).json()["results"] == []
    with TestClient(create_app(make_engine(url), folder)) as restarted:
        assert restarted.get("/api/documents").json() == []
    assert list(folder.iterdir()) == []
