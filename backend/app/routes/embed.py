from uuid import UUID
from fastapi import APIRouter, HTTPException
from app import config
from app.services import store, pdf_utils

router = APIRouter(prefix="/embed")


@router.post("/{pdf_id}")
def embed_pdf(pdf_id: UUID):
    book_id = str(pdf_id)
    if not store.get_book(book_id):
        raise HTTPException(404, "Document not found.")
    try:
        passages, metadata = pdf_utils.extract_and_clean(config.UPLOAD_DIR / f"{book_id}.pdf")
        vectors = None
        if config.RETRIEVAL_MODE == "semantic":
            from app.services.embedding import get_embeddings

            vectors = get_embeddings([p["text"] for p in passages])
        store.replace_passages(book_id, passages, vectors)
        return {
            "status": "ready",
            "chunks": len(passages),
            "sparse_pages": metadata["sparse_pages"],
            "retrieval": config.RETRIEVAL_MODE,
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except ImportError:
        raise HTTPException(503, "Install requirements-semantic.txt to use semantic retrieval.")
    except Exception:
        raise HTTPException(500, "Indexing failed. Your previous index is preserved; retry with a smaller document.")
