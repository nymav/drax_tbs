from fastapi import APIRouter, HTTPException
import os
import json
from pathlib import Path

router = APIRouter()

@router.get("/textbooks")
def list_textbooks():
    pdf_dir = "data/pdfs"
    metadata_path = "data/textbooks.json"
    
    # Create directories if they don't exist
    Path(pdf_dir).mkdir(parents=True, exist_ok=True)
    
    # Check if PDF directory exists and is accessible
    if not os.path.exists(pdf_dir):
        raise HTTPException(status_code=500, detail=f"PDF directory '{pdf_dir}' not found")
    
    metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load metadata: {e}")
            metadata = {}
    
    files = []
    try:
        for filename in os.listdir(pdf_dir):
            if filename.endswith(".pdf"):
                # Extract the UUID from filename (remove .pdf extension)
                file_id = filename.rsplit('.', 1)[0]
                meta = metadata.get(file_id, {})
                
                if isinstance(meta, dict):
                    # Use title as primary display name, fallback to original_name, then filename
                    title = meta.get("title") or meta.get("original_name") or filename
                    files.append({
                        "id": file_id,  # Use UUID as ID
                        "filename": filename,  # Keep original filename for compatibility
                        "title": title,  # Display title
                        "name": title,  # Alias for compatibility with frontend
                        "author": meta.get("author", "Unknown"),
                        "pages": meta.get("pages", "?"),
                        "original_name": meta.get("original_name", filename)
                    })
                else:
                    # Fallback for old format
                    files.append({
                        "id": file_id,
                        "filename": filename,
                        "title": meta if isinstance(meta, str) else filename,
                        "name": meta if isinstance(meta, str) else filename,
                        "author": "Unknown",
                        "pages": "?",
                        "original_name": filename
                    })
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"PDF directory '{pdf_dir}' not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Cannot access PDF directory '{pdf_dir}'")
    except Exception as e:
        print(f"Error reading PDF directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to read PDF directory")
    
    return files