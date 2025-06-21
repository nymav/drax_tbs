from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil, uuid, os, json
from pathlib import Path
import fitz  # PyMuPDF
from app.config import UPLOAD_DIR

router = APIRouter()

@router.post("/uploads")
async def upload_pdf(file: UploadFile = File(...)):
    # Generate unique filename
    orig_name = file.filename.rsplit('.', 1)[0]
    file_uuid = str(uuid.uuid4())
    filename = f"{file_uuid}.pdf"
    save_path = UPLOAD_DIR / filename

    try:
        # Save uploaded PDF to disk
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"📄 Saved PDF: {save_path}")
    except Exception as e:
        print(f"❌ Failed to save PDF: {e}")
        raise HTTPException(status_code=500, detail="File saving failed.")

    # Try to extract metadata using PyMuPDF
    try:
        doc = fitz.open(str(save_path))
        meta = doc.metadata or {}
        title = (meta.get("title") or orig_name).strip()
        author = (meta.get("author") or "Unknown").strip()
        page_count = len(doc)
    except Exception as e:
        print(f"⚠️ Metadata extraction failed: {e}")
        title = orig_name
        author = "Unknown"
        page_count = "?"

    # Load or create metadata file
    metadata_path = Path("data/textbooks.json")
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

    # Update metadata for this PDF
    metadata[file_uuid] = {
        "title": title,
        "author": author,
        "pages": page_count,
        "chapters": [],
        "original_name": orig_name
    }

    # Save updated metadata
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # ✅ Return clean response to frontend
    return {
        "pdf_id": file_uuid,
        "title": title,
        "author": author,
        "pages": page_count
    }