from fastapi import APIRouter
import sqlite3
from app.config import BASE_DIR

router = APIRouter(prefix="/sessions")
DB_PATH = BASE_DIR / "db/chat_history.db"

@router.get("/{session_id}")
def get_history(session_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT role, query, answer FROM history WHERE session_id=?", (session_id,))
        rows = cur.fetchall()
    return [{"role": r, "query": q, "answer": a} for r, q, a in rows]
