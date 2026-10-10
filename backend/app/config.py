"""Configuration is independent of the shell's working directory."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.getenv("DRAX_DATA_DIR", str(BASE_DIR / ".drax-data"))).resolve()
UPLOAD_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "workspace.sqlite3"
MAX_FILE_BYTES = int(os.getenv("DRAX_MAX_FILE_MB", "25")) * 1024 * 1024
MAX_PAGES = int(os.getenv("DRAX_MAX_PAGES", "600"))
API_KEY = os.getenv("DRAX_API_KEY", "")
CORS_ORIGINS = os.getenv("DRAX_CORS_ORIGINS", "http://localhost:5177,http://127.0.0.1:5177").split(",")
LMSTUDIO_API = os.getenv("LMSTUDIO_API", "http://127.0.0.1:1234/v1/chat/completions")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "")
RETRIEVAL_MODE = os.getenv("DRAX_RETRIEVAL", "lexical")
EMBEDDING_MODEL = os.getenv("DRAX_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
