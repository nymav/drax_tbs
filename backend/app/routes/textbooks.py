from uuid import UUID
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app import config
from app.services import store

router = APIRouter()


@router.get("/textbooks")
def list_textbooks():
    return store.list_books()


@router.get("/textbooks/{book_id}/pdf")
def open_pdf(book_id: UUID):
    book = store.get_book(str(book_id))
    path = config.UPLOAD_DIR / f"{book_id}.pdf"
    if not book or not path.exists():
        raise HTTPException(404, "Document not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="document.pdf",
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/textbooks/{book_id}", status_code=204)
def delete_book(book_id: UUID):
    if not store.get_book(str(book_id)):
        raise HTTPException(404, "Document not found.")
    store.delete_book(str(book_id))
    (config.UPLOAD_DIR / f"{book_id}.pdf").unlink(missing_ok=True)
