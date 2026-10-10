import uuid
import hashlib
import sqlite3
from pathlib import Path
import pymupdf as fitz
from fastapi import APIRouter, UploadFile, File, HTTPException
from app import config
from app.services import store

router = APIRouter()


@router.post("/uploads", status_code=201)
def upload_pdf(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Choose a PDF document.")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    book_id = str(uuid.uuid4())
    path = config.UPLOAD_DIR / f"{book_id}.pdf"
    size = 0
    digest = hashlib.sha256()
    try:
        with path.open("wb") as target:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > config.MAX_FILE_BYTES:
                    raise HTTPException(413, f"PDFs must be smaller than {config.MAX_FILE_BYTES // 1024 // 1024} MB.")
                target.write(chunk)
                digest.update(chunk)
        with fitz.open(path) as doc:
            if not doc.is_pdf:
                raise HTTPException(415, "This file is not a valid PDF.")
            if doc.needs_pass:
                raise HTTPException(422, "Unlock the password-protected PDF before upload.")
            if not 0 < len(doc) <= config.MAX_PAGES:
                raise HTTPException(422, f"PDF must have 1–{config.MAX_PAGES} pages.")
            metadata = doc.metadata or {}
            title = (metadata.get("title") or Path(file.filename).stem).strip()[:180]
            author = (metadata.get("author") or "Unknown author").strip()[:180]
            pages = len(doc)
        # Content-addressed duplicate detection (no filename-based guesses).
        for existing in store.list_books():
            existing_path = config.UPLOAD_DIR / f"{existing['id']}.pdf"
            if existing_path.exists() and hashlib.sha256(existing_path.read_bytes()).hexdigest() == digest.hexdigest():
                path.unlink()
                return {**existing, "pdf_id": existing["id"], "duplicate": True}
        try:
            store.add_book(book_id, title, author, pages, digest.hexdigest())
        except sqlite3.IntegrityError:
            with store.connect() as db:
                duplicate = db.execute("SELECT * FROM books WHERE file_hash=?", (digest.hexdigest(),)).fetchone()
            if not duplicate:
                raise
            path.unlink()
            return {**dict(duplicate), "pdf_id": duplicate["id"], "duplicate": True}
        return {
            "pdf_id": book_id,
            "id": book_id,
            "title": title,
            "author": author,
            "pages": pages,
            "status": "uploaded",
        }
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except (fitz.FileDataError, fitz.EmptyFileError, RuntimeError, ValueError):
        path.unlink(missing_ok=True)
        raise HTTPException(422, "The PDF is empty or damaged. Try exporting a new copy.")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()
