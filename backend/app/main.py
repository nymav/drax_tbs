from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import uploads, embed, chat, sessions, textbooks
from app.config import UPLOAD_DIR

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# Allow frontend (localhost:5173) to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Consistent API prefix for clarity and separation
app.include_router(uploads.router, prefix="/api")
app.include_router(embed.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(textbooks.router, prefix="/api")