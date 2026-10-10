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
    db = sqlite3.connect(config.DB_PATH, timeout=30)
    try:
        with db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA busy_timeout=30000")
            if db.execute("PRAGMA user_version").fetchone()[0] == 0:
                db.executescript("""
          CREATE TABLE IF NOT EXISTS books(id TEXT PRIMARY KEY,title TEXT,author TEXT,pages INTEGER,status TEXT DEFAULT 'uploaded',created_at TEXT);
          CREATE TABLE IF NOT EXISTS passages(id INTEGER PRIMARY KEY,book_id TEXT REFERENCES books(id) ON DELETE CASCADE,page INTEGER,text TEXT,vector TEXT);
          CREATE VIRTUAL TABLE IF NOT EXISTS passage_search USING fts5(text,book_id UNINDEXED,page UNINDEXED,tokenize='porter unicode61');
          CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,book_id TEXT REFERENCES books(id) ON DELETE CASCADE,title TEXT,created_at TEXT);
          CREATE TABLE IF NOT EXISTS turns(id INTEGER PRIMARY KEY,session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,query TEXT,response TEXT,created_at TEXT);
          """)
            migrate(db)
            migrate_hash(db)
            migrate_hierarchy(db)
            yield db
    finally:
        db.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def get_book(book_id):
    with connect() as db:
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None


def list_books():
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM books ORDER BY created_at DESC")]


def add_book(book_id, title, author, pages, file_hash=None):
    with connect() as db:
        db.execute(
            "INSERT INTO books(id,title,author,pages,status,created_at,file_hash) VALUES(?,?,?,?,?,?,?)",
            (book_id, title, author, pages, "uploaded", now(), file_hash),
        )


def replace_passages(book_id, passages, vectors=None, job_id=None, job_result=None):
    # Build the replacement outside the write transaction, then commit together.
    from app.services.index_version import fingerprint
    from app.services.hierarchy import build

    version = fingerprint(book_id, vectors)
    nodes = build(get_book(book_id), passages)["sections"]
    with connect() as db:
        db.execute("DELETE FROM hierarchy_nodes WHERE book_id=?", (book_id,))
        for ordinal, node in enumerate(nodes):
            db.execute(
                "INSERT INTO hierarchy_nodes(book_id,id,ordinal,node) VALUES(?,?,?,?)",
                (book_id, node["id"], ordinal, json.dumps(node)),
            )
        db.execute("DELETE FROM passages WHERE book_id=?", (book_id,))
        db.execute("DELETE FROM passage_search WHERE book_id=?", (book_id,))
        for i, p in enumerate(passages):
            db.execute(
                "INSERT INTO passages(book_id,page,text,vector,structure) VALUES(?,?,?,?,?)",
                (
                    book_id,
                    p["page"],
                    p["text"],
                    json.dumps(vectors[i]) if vectors else None,
                    json.dumps(p.get("structure", {})),
                ),
            )
            db.execute(
                "INSERT INTO passage_search(rowid,text,book_id,page) VALUES(last_insert_rowid(),?,?,?)",
                (p["text"], book_id, p["page"]),
            )
        db.execute("UPDATE books SET status='ready',index_version=? WHERE id=?", (json.dumps(version), book_id))
        if job_id:
            db.execute(
                "UPDATE jobs SET state='completed',progress=1,result=?,updated_at=? WHERE id=?",
                (json.dumps(job_result), now(), job_id),
            )


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
            "SELECT rowid AS id,page,text,bm25(passage_search) AS score FROM passage_search WHERE passage_search MATCH ? AND book_id=? AND (? IS NULL OR page>=?) AND (? IS NULL OR page<=?) ORDER BY score LIMIT ?",
            (match, book_id, page_from, page_from, page_to, page_to, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def page_passages(book_id, start=None, end=None, limit=6):
    with connect() as db:
        rows = db.execute(
            "SELECT id,page,text,structure FROM passages WHERE book_id=? AND (? IS NULL OR page>=?) AND (? IS NULL OR page<=?) ORDER BY page,id LIMIT ?",
            (book_id, start, start, end, end, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_book(book_id):
    with connect() as db:
        db.execute("DELETE FROM passage_search WHERE book_id=?", (book_id,))
        db.execute("DELETE FROM books WHERE id=?", (book_id,))


def create_session(session_id, book_id, title):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO sessions VALUES(?,?,?,?)", (session_id, book_id, title[:80], now()))


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


def migrate(db):
    """Versioned, transactional migration; existing workspaces remain readable."""
    if db.execute("PRAGMA user_version").fetchone()[0] >= 1:
        return
    db.execute("BEGIN IMMEDIATE")
    # Recheck after taking the writer lock: another process may have migrated.
    if db.execute("PRAGMA user_version").fetchone()[0] >= 1:
        return
    db.execute("ALTER TABLE books ADD COLUMN index_version TEXT")
    db.execute("ALTER TABLE passages ADD COLUMN structure TEXT DEFAULT '{}'")
    db.execute("CREATE INDEX passages_scope ON passages(book_id,page,id)")
    db.execute("CREATE INDEX sessions_book ON sessions(book_id,created_at)")
    db.execute("CREATE INDEX turns_session ON turns(session_id,id)")
    db.execute(
        "CREATE TABLE jobs(id TEXT PRIMARY KEY,book_id TEXT REFERENCES books(id) ON DELETE CASCADE,state TEXT,payload TEXT,result TEXT,error TEXT,attempt INTEGER DEFAULT 0,progress REAL DEFAULT 0,updated_at TEXT)"
    )
    db.execute("CREATE UNIQUE INDEX jobs_active ON jobs(book_id) WHERE state IN ('queued','running')")
    db.execute("PRAGMA user_version=1")
    db.commit()


def migrate_hash(db):
    if db.execute("PRAGMA user_version").fetchone()[0] >= 2:
        return
    db.execute("BEGIN IMMEDIATE")
    if db.execute("PRAGMA user_version").fetchone()[0] < 2:
        db.execute("ALTER TABLE books ADD COLUMN file_hash TEXT")
        db.execute("CREATE UNIQUE INDEX books_hash ON books(file_hash) WHERE file_hash IS NOT NULL")
        # Rebuild FTS IDs to match existing passage IDs on upgraded workspaces.
        db.execute("DELETE FROM passage_search")
        db.execute("INSERT INTO passage_search(rowid,text,book_id,page) SELECT id,text,book_id,page FROM passages")
        db.execute("PRAGMA user_version=2")
    db.commit()


def migrate_hierarchy(db):
    if db.execute("PRAGMA user_version").fetchone()[0] >= 3:
        return
    db.execute("BEGIN IMMEDIATE")
    if db.execute("PRAGMA user_version").fetchone()[0] < 3:
        db.execute(
            "CREATE TABLE hierarchy_nodes(book_id TEXT REFERENCES books(id) ON DELETE CASCADE,id TEXT,ordinal INTEGER,node TEXT,PRIMARY KEY(book_id,id))"
        )
        db.execute("CREATE INDEX hierarchy_book_order ON hierarchy_nodes(book_id,ordinal)")
        db.execute("PRAGMA user_version=3")
    db.commit()
