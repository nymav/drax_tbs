import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path("data/pdfs")
EMBEDDINGS_DIR = BASE_DIR / "data/embeddings"
VECTOR_DB_DIR = BASE_DIR / "data/vector_store"
LMSTUDIO_API = os.getenv("LMSTUDIO_API", "http://localhost:1234/v1/chat/completions")
