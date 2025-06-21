from fastapi import APIRouter, HTTPException
from pathlib import Path
import traceback

from app.services import pdf_utils, embedding, vector_store
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/embed", tags=["embed"])

@router.post("/{pdf_id}")
async def embed_pdf(pdf_id: str):
    """
    Given a pdf_id (without .pdf extension), load the file,
    extract & clean text into chunks, embed them, and persist to vector store.
    """
    # 1) Locate the PDF on disk
    pdf_path = UPLOAD_DIR / f"{pdf_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    try:
        # 2) Extract and clean into chunks
        chunks, metadata = pdf_utils.extract_and_clean(pdf_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text chunks extracted from PDF.")
        
        # 3) Embed all chunks
        vectors = embedding.get_embeddings(chunks)
        if not vectors or len(vectors) != len(chunks):
            raise HTTPException(
                status_code=500,
                detail=f"Embedding failure: expected {len(chunks)} vectors, got {len(vectors) if vectors is not None else 0}."
            )

        # 4) Persist to your vector store
        vector_store.save_vectors(pdf_id, chunks, vectors)

    except HTTPException:
        # re-raise known HTTP errors
        raise
    except Exception as e:
        # log full traceback, then return generic 500
        print(f"[EMBED ERROR] Failed embedding {pdf_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # 5) All done!
    return {"status": "embedded", "chunks": len(chunks)}