"""Bounded local extraction subprocess; never executes uploaded content."""
import json
import re
import sys
from pathlib import Path

MAX_TEXT = 2_000_000
MAX_PAGES = 200


def extract(path: Path):
    segments = []
    warning = None
    page_count = 0
    if path.suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported. Upload an unencrypted copy.")
        page_count = len(reader.pages)
        if not page_count:
            raise ValueError("The PDF has no pages. Upload a document containing text.")
        if page_count > MAX_PAGES:
            raise ValueError("This local demo supports at most 200 PDF pages per document. Split the PDF and retry.")
        total = 0
        empty = []
        for number, page in enumerate(reader.pages, 1):
            content = page.get_contents()
            if content and len(content.get_data()) > 10 * 1024 * 1024:
                raise ValueError("A PDF page is too complex to extract locally. Simplify or split the document.")
            text = (page.extract_text() or "").strip()
            total += len(text)
            if total > MAX_TEXT:
                raise ValueError("Extracted text exceeds the 2 million character limit. Split the document.")
            if text:
                segments.append({"text": text, "page": number, "section": None})
            else:
                empty.append(number)
        if not segments:
            return {"status": "needs_ocr", "error": "This PDF has no extractable text. Scanned pages require OCR, which is not included. Upload a text-based PDF or TXT/Markdown copy.", "segments": [], "page_count": page_count, "warning": None}
        if empty:
            warning = "Pages without extractable text were omitted: " + ", ".join(map(str, empty)) + ". Image-only pages require OCR."
    else:
        raw = path.read_bytes()
        encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        try:
            text = raw.decode(encoding)
        except UnicodeError:
            raise ValueError("Text files must use UTF-8 or UTF-16 with a byte-order mark. Save a text copy and retry.")
        if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
            raise ValueError("The file contains binary control characters. Upload a plain text document.")
        if len(text) > MAX_TEXT:
            raise ValueError("Extracted text exceeds the 2 million character limit. Split the document.")
        if not text.strip():
            raise ValueError("The document contains no text. Upload a non-empty document.")
        if path.suffix == ".md":
            section = None
            lines = []
            def flush():
                if "\n".join(lines).strip():
                    segments.append({"text": "\n".join(lines).strip(), "page": None, "section": section})
            fenced = False
            for line in text.splitlines():
                if line.lstrip().startswith(("```", "~~~")):
                    fenced = not fenced
                match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line) if not fenced else None
                if match:
                    flush()
                    lines = [line]
                    section = match.group(1)
                else:
                    lines.append(line)
            flush()
        else:
            segments = [{"text": text.strip(), "page": None, "section": None}]
    return {"status": "ready", "segments": segments, "page_count": page_count, "warning": warning, "error": None}


if __name__ == "__main__":
    try:
        result = extract(Path(sys.argv[1]))
    except ValueError as error:
        result = {"status": "failed", "error": str(error), "segments": [], "page_count": 0, "warning": None}
    except Exception:
        result = {"status": "failed", "error": "The document could not be read. It may be damaged or use an unsupported PDF structure. Export a text-based copy and retry.", "segments": [], "page_count": 0, "warning": None}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode("utf-8"))
