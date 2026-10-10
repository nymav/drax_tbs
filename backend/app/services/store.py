"""Small, persistent, single-user study library with atomic indexing."""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from app import config


@contextmanager
def connect():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.DB_PATH, timeout=30) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS books(id TEXT PRIMARY KEY,title TEXT,author TEXT,pages INTEGER,status TEXT DEFAULT 'uploaded',created_at TEXT);
        CREATE TABLE IF NOT EXISTS passages(id INTEGER PRIMARY KEY,book_id TEXT REFERENCES books(id) ON DELETE CASCADE,page INTEGER,text TEXT,vector TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS passage_search USING fts5(text,book_id UNINDEXED,page UNINDEXED,tokenize='porter unicode61');
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,book_id TEXT REFERENCES books(id) ON DELETE CASCADE,title TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS turns(id INTEGER PRIMARY KEY,session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,query TEXT,response TEXT,created_at TEXT);
        """)
        yield db


def now():
    return datetime.now(timezone.utc).isoformat()


def get_book(book_id):
    with connect() as db:
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None


def list_books():
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM books ORDER BY created_at DESC")]


def add_book(book_id, title, author, pages):
    with connect() as db:
        db.execute("INSERT INTO books VALUES(?,?,?,?,?,?)", (book_id, title, author, pages, "uploaded", now()))


def replace_passages(book_id, passages, vectors=None):
    # A failed extraction/embedding leaves the previous index untouched.
    with connect() as db:
        db.execute("DELETE FROM passages WHERE book_id=?", (book_id,))
        db.execute("DELETE FROM passage_search WHERE book_id=?", (book_id,))
        for i, p in enumerate(passages):
            db.execute(
                "INSERT INTO passages(book_id,page,text,vector) VALUES(?,?,?,?)",
                (book_id, p["page"], p["text"], json.dumps(vectors[i]) if vectors else None),
            )
            db.execute("INSERT INTO passage_search VALUES(?,?,?)", (p["text"], book_id, p["page"]))
        db.execute("UPDATE books SET status='ready' WHERE id=?", (book_id,))


def search(book_id, query, page_from=None, page_to=None, limit=6):
    # Bound tokens and use quoted terms: user text never becomes raw FTS syntax.
    words = list(dict.fromkeys(re.findall(r"[\w]+", query.lower())))[:24]
    stop = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "of",
        "to",
        "in",
        "and",
        "it",
        "what",
        "how",
        "explain",
        "me",
        "please",
        "about",
        "this",
    }
    words = [w for w in words if w not in stop]
    if not words:
        return []
    match = " OR ".join('"' + w + '"' for w in words)
    with connect() as db:
        rows = db.execute(
            "SELECT page,text,bm25(passage_search) AS score FROM passage_search WHERE passage_search MATCH ? AND book_id=? AND (? IS NULL OR page>=?) AND (? IS NULL OR page<=?) ORDER BY score LIMIT ?",
            (match, book_id, page_from, page_from, page_to, page_to, limit),
        ).fetchall()
        return [{"page": r["page"], "text": r["text"]} for r in rows]


def page_passages(book_id, start=None, end=None, limit=6):
    with connect() as db:
        rows = db.execute(
            "SELECT page,text FROM passages WHERE book_id=? AND (? IS NULL OR page>=?) AND (? IS NULL OR page<=?) ORDER BY page,id LIMIT ?",
            (book_id, start, start, end, end, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_book(book_id):
    with connect() as db:
        db.execute("DELETE FROM passage_search WHERE book_id=?", (book_id,))
        db.execute("DELETE FROM books WHERE id=?", (book_id,))


def create_session(session_id, book_id, title):
    with connect() as db:
        db.execute("INSERT INTO sessions VALUES(?,?,?,?)", (session_id, book_id, title[:80], now()))


def get_session(session_id):
    with connect() as db:
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None


def list_sessions(book_id):
    with connect() as db:
        return [
            dict(r) for r in db.execute("SELECT * FROM sessions WHERE book_id=? ORDER BY created_at DESC", (book_id,))
        ]


def save_turn(session_id, query, response):
    with connect() as db:
        db.execute(
            "INSERT INTO turns(session_id,query,response,created_at) VALUES(?,?,?,?)",
            (session_id, query, json.dumps(response), now()),
        )


def history(session_id):
    with connect() as db:
        return [
            {"query": r["query"], "response": json.loads(r["response"]), "created_at": r["created_at"]}
            for r in db.execute("SELECT * FROM turns WHERE session_id=? ORDER BY id", (session_id,))
        ]


def delete_session(session_id):
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
