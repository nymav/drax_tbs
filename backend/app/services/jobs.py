"""Persistent single-worker queue with process-level cancellation and recovery."""

import multiprocessing
import json
import threading
import time
import uuid
from app import config
from app.services import store

_guard = threading.Lock()
_processes = {}


def enqueue(book_id, kind="index"):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        active = db.execute(
            "SELECT id,payload FROM jobs WHERE book_id=? AND state IN ('queued','running')", (book_id,)
        ).fetchone()
        if active:
            if (json.loads(active["payload"] or "{}").get("kind", "index")) != kind:
                raise ValueError("Another job for this document is active. Wait or cancel it first.")
            return active["id"]
        identity = str(uuid.uuid4())
        db.execute(
            "INSERT INTO jobs(id,book_id,state,updated_at,payload) VALUES(?,?,'queued',?,?)",
            (identity, book_id, store.now(), json.dumps({"kind": kind})),
        )
        return identity


def get(identity):
    with store.connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone()
        return dict(row) if row else None


def cancel(identity):
    with _guard:
        process = _processes.get(identity)
        if process:
            process.terminate()
            process.join(5)
        with store.connect() as db:
            db.execute(
                "UPDATE jobs SET state='cancelled',updated_at=? WHERE id=? AND state IN ('queued','running')",
                (store.now(), identity),
            )


def _index(identity, book_id, data_dir, db_path, upload_dir):
    # Spawned workers get explicit paths (also isolates test workspaces).
    config.DATA_DIR, config.DB_PATH, config.UPLOAD_DIR = data_dir, db_path, upload_dir
    from app.services import pdf_utils

    try:
        if json.loads(get(identity)["payload"] or "{}").get("kind") == "summary":
            from app.services.hierarchy import generated_summary
            from app.services.index_version import stale

            if stale(store.get_book(book_id)):
                raise ValueError("Re-index this document before summarizing.")

            def summary_progress(fraction):
                with store.connect() as db:
                    db.execute("UPDATE jobs SET progress=?,updated_at=? WHERE id=?", (fraction, store.now(), identity))

            result = generated_summary(book_id, summary_progress)
            with store.connect() as db:
                db.execute(
                    "UPDATE jobs SET state='completed',progress=1,result=?,updated_at=? WHERE id=?",
                    (json.dumps(result), store.now(), identity),
                )
            return

        def progress(page, total):
            with store.connect() as db:
                db.execute(
                    "UPDATE jobs SET progress=?,updated_at=? WHERE id=?", (0.5 * page / total, store.now(), identity)
                )

        passages, metadata = pdf_utils.extract_and_clean(config.UPLOAD_DIR / f"{book_id}.pdf", progress=progress)
        with store.connect() as db:
            db.execute("UPDATE jobs SET progress=.5,updated_at=? WHERE id=?", (store.now(), identity))
        vectors = None
        if config.RETRIEVAL_MODE in {"semantic", "hybrid"}:
            from app.services.embedding import get_embeddings

            vectors = get_embeddings([p["text"] for p in passages])
        store.replace_passages(
            book_id, passages, vectors, job_id=identity, job_result={"chunks": len(passages), **metadata}
        )
    except Exception as exc:
        with store.connect() as db:
            db.execute(
                "UPDATE jobs SET state=CASE WHEN attempt<3 THEN 'queued' ELSE 'failed' END,error=?,updated_at=? WHERE id=?",
                (str(exc)[:500], store.now(), identity),
            )


def run(stop):
    while not stop.wait(0.3):
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY updated_at LIMIT 1").fetchone()
            if not row:
                continue
            db.execute(
                "UPDATE jobs SET state='running',attempt=attempt+1,updated_at=? WHERE id=?", (store.now(), row["id"])
            )
        process = multiprocessing.get_context("spawn").Process(
            target=_index, args=(row["id"], row["book_id"], config.DATA_DIR, config.DB_PATH, config.UPLOAD_DIR)
        )
        with _guard:
            if get(row["id"])["state"] == "cancelled":
                continue
            _processes[row["id"]] = process
            process.start()
        while process.is_alive() and not stop.wait(0.2):
            pass
        with _guard:
            if process.is_alive():
                process.terminate()
            process.join(5)
            _processes.pop(row["id"], None)
        with store.connect() as db:
            db.execute(
                "UPDATE jobs SET state=CASE WHEN attempt<3 THEN 'queued' ELSE 'failed' END,error='Worker stopped; retrying',updated_at=? WHERE id=? AND state='running'",
                (store.now(), row["id"]),
            )
        time.sleep(0.1)


def start():
    from filelock import FileLock, Timeout

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    owner = FileLock(config.DATA_DIR / "queue.lock", thread_local=False)
    try:
        owner.acquire(timeout=0)
    except Timeout as exc:
        raise RuntimeError("This workspace already has a worker. Run one uvicorn process per workspace.") from exc
    # Enforce one process owning the durable queue, including restart recovery.
    with store.connect() as db:
        db.execute("UPDATE jobs SET state=CASE WHEN attempt<3 THEN 'queued' ELSE 'failed' END WHERE state='running'")
    stop = threading.Event()

    def guarded_run():
        try:
            run(stop)
        finally:
            owner.release()

    thread = threading.Thread(target=guarded_run, daemon=True)
    thread.start()
    return stop, thread
