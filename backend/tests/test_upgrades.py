import json
import threading
import pytest
from app import config
from app.services import store, jobs, lmstudio
from app.services.backup import backup, restore, verify
from app.services.hierarchy import tree, summarize
from app.services.index_version import stale
from test_workspace import indexed, upload


def test_structure_hierarchy_and_full_digest(client):
    book = indexed(client)
    passages = store.page_passages(book)
    structure = json.loads(passages[0]["structure"])
    assert structure["blocks"][0]["bbox"] and structure["page_size"]
    assert tree(book)["sections"][0]["page_from"] == 1
    digest = summarize(book)
    assert digest["coverage"] == {"passages": 2, "indexed_pages": 2}
    assert all(
        note["quote"] in next(p["text"] for p in passages if p["id"] == note["passage_id"])
        for section in digest["sections"]
        for note in section["notes"]
    )


def test_stale_file_is_rejected(client):
    book = indexed(client)
    assert not stale(store.get_book(book))
    path = config.UPLOAD_DIR / f"{book}.pdf"
    path.write_bytes(path.read_bytes() + b"\nchanged")
    assert stale(store.get_book(book))
    assert client.post("/api/chat/", json={"pdf_id": book, "query": "chlorophyll"}).status_code == 409


def test_jobs_deduplicate_cancel_and_recover(client):
    book = upload(client)
    first = jobs.enqueue(book)
    assert jobs.enqueue(book) == first
    jobs.cancel(first)
    assert jobs.get(first)["state"] == "cancelled"
    second = jobs.enqueue(book)
    assert second != first
    with store.connect() as db:
        db.execute("UPDATE jobs SET state='running',attempt=1 WHERE id=?", (second,))
    stop, thread = jobs.start()
    stop.set()
    thread.join(2)
    assert jobs.get(second)["state"] == "queued"


def test_real_worker_and_atomic_index_completion(client):
    book = upload(client)
    identity = jobs.enqueue(book)
    with store.connect() as db:
        db.execute("UPDATE jobs SET state='running',attempt=1 WHERE id=?", (identity,))
    jobs._index(identity, book, config.DATA_DIR, config.DB_PATH, config.UPLOAD_DIR)
    assert jobs.get(identity)["state"] == "completed"
    assert store.get_book(book)["status"] == "ready"
    assert json.loads(jobs.get(identity)["result"])["chunks"] == 2


def test_quote_membership_and_context_budget(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(lmstudio, "count_tokens", lambda model, system, prompt: len((system + prompt).encode()) + 256)
    prompt = "[S1] Page 1: Photosynthesis uses chlorophyll.\nLearner request: explain"
    lmstudio.validate_claims({"claims": [{"source_id": "S1", "quote": "uses chlorophyll."}]}, prompt)
    with pytest.raises(ValueError):
        lmstudio.validate_claims({"claims": [{"source_id": "S1", "quote": "invented quotation"}]}, prompt)
    monkeypatch.setattr(config, "LMSTUDIO_MODEL", "test")
    monkeypatch.setattr(lmstudio, "loaded_context", lambda model: 300)
    monkeypatch.setattr(lmstudio.requests, "post", lambda *a, **kw: pytest.fail("Oversized request reached provider"))
    with pytest.raises(lmstudio.ModelUnavailable, match="context"):
        lmstudio.ask_local_llm(prompt, "system")


def test_backup_restore_integrity_and_tampering(client, tmp_path):
    book = indexed(client)
    destination = tmp_path / "snapshot"
    backup(destination)
    verify(destination)
    restored = tmp_path / "restored"
    restore(destination, restored)
    import sqlite3

    with sqlite3.connect(restored / "workspace.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM passages").fetchone()[0] == 2
    assert (restored / "pdfs" / f"{book}.pdf").exists()
    (destination / "pdfs" / f"{book}.pdf").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        verify(destination)


def test_concurrent_turns_preserve_every_response(client):
    book = indexed(client)
    session = "a9c0e266-8049-45cf-8dc0-14f406d75549"
    store.create_session(session, book, "Concurrency")
    errors = []

    def write(index):
        try:
            store.save_turn(session, str(index), {"answer": str(index)})
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors and len(store.history(session)) == 12


def test_failed_job_keeps_previous_index(client):
    book = indexed(client)
    original = store.page_passages(book)
    (config.UPLOAD_DIR / f"{book}.pdf").write_bytes(b"broken")
    identity = jobs.enqueue(book)
    for attempt in range(1, 4):
        with store.connect() as db:
            db.execute("UPDATE jobs SET state='running',attempt=? WHERE id=?", (attempt, identity))
        jobs._index(identity, book, config.DATA_DIR, config.DB_PATH, config.UPLOAD_DIR)
    assert jobs.get(identity)["state"] == "failed"
    assert store.page_passages(book) == original


def test_budget_prunes_low_ranked_evidence_before_generation():
    prompt = "Sources:\n[S1] Page 1: " + "a" * 500 + "\n\n[S2] Page 2: " + "b" * 500 + "\nLearner request: explain"
    trimmed, bound, output = lmstudio.budget_prompt(prompt, "system", 1100, 600)
    assert "[S1]" in trimmed and "[S2]" not in trimmed
    assert bound + output <= 1100 and output >= 256


def _slow_worker(identity, book_id, data_dir, db_path, upload_dir):
    import time

    time.sleep(20)
    (data_dir / "should-not-exist").write_text("Worker survived cancellation")


def test_running_job_really_stops_child_process(client, monkeypatch):
    import time

    book = upload(client)
    identity = jobs.enqueue(book)
    monkeypatch.setattr(jobs, "_index", _slow_worker)
    stop, thread = jobs.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with jobs._guard:
                process = jobs._processes.get(identity)
                started = process is not None and process.is_alive()
            if started:
                break
            time.sleep(0.05)
        assert started
        jobs.cancel(identity)
        assert not process.is_alive()
        assert jobs.get(identity)["state"] == "cancelled"
        assert store.get_book(book)["status"] == "uploaded"
        assert not (config.DATA_DIR / "should-not-exist").exists()
    finally:
        stop.set()
        thread.join(5)


def test_pdf_tables_outline_and_section_filter(client):
    import io
    import pymupdf as fitz

    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), "Cell biology", fontsize=24)
        for y in [100, 140, 180]:
            page.draw_line((50, y), (350, y))
        for x in [50, 200, 350]:
            page.draw_line((x, 100), (x, 180))
        for x, y, text in [
            (65, 125, "Organelle"),
            (215, 125, "Function"),
            (65, 165, "Mitochondria"),
            (215, 165, "Respiration"),
        ]:
            page.insert_text((x, y), text, fontsize=10)
        page = doc.new_page()
        page.insert_text((50, 60), "Appendix describes photosynthesis and chlorophyll.")
        doc.set_toc([[1, "Cell biology", 1], [2, "Organelles", 1], [1, "Appendix", 2]])
        data = doc.tobytes()
    book = client.post("/api/uploads", files={"file": ("table.pdf", io.BytesIO(data), "application/pdf")}).json()["id"]
    assert client.post("/api/embed/" + book).status_code == 200
    passages = store.page_passages(book)
    tables = [json.loads(p["structure"]) for p in passages if json.loads(p["structure"]).get("kind") == "table"]
    assert tables and tables[0]["tables"][1] == ["Mitochondria", "Respiration"]
    nodes = tree(book)["sections"]
    assert nodes[1]["parent"] == nodes[0]["id"]
    result = client.post("/api/chat/", json={"pdf_id": book, "query": "chlorophyll", "section_id": nodes[0]["id"]})
    assert result.json()["mode"] == "no_match"


def test_staged_summary_carries_original_quotes(client, monkeypatch):
    book = indexed(client)

    def generated(prompt, system, **kwargs):
        identity, text = next(iter(kwargs["evidence"].items()))
        return lmstudio.GeneratedAnswer("Summary", [{"claim": "Key idea", "source_id": identity, "quote": text}], {})

    monkeypatch.setattr(lmstudio, "ask_local_llm", generated)
    from app.services.hierarchy import generated_summary

    result = generated_summary(book)
    assert result["coverage"]["submitted_passages"] == 2
    assert result["sections"][0]["claims"][0]["quote"] == store.page_passages(book)[0]["text"]


def test_migration_preserves_unversioned_workspace(client):
    import sqlite3

    with sqlite3.connect(config.DB_PATH) as db:
        db.executescript("""
        CREATE TABLE books(id TEXT PRIMARY KEY,title TEXT,author TEXT,pages INTEGER,status TEXT,created_at TEXT);
        CREATE TABLE passages(id INTEGER PRIMARY KEY,book_id TEXT,page INTEGER,text TEXT,vector TEXT);
        CREATE VIRTUAL TABLE passage_search USING fts5(text,book_id UNINDEXED,page UNINDEXED);
        CREATE TABLE sessions(id TEXT PRIMARY KEY,book_id TEXT,title TEXT,created_at TEXT);
        CREATE TABLE turns(id INTEGER PRIMARY KEY,session_id TEXT,query TEXT,response TEXT,created_at TEXT);
        INSERT INTO books VALUES('legacy','Legacy','Author',1,'ready','now');
        INSERT INTO passages VALUES(42,'legacy',1,'Legacy photosynthesis passage',NULL);
        INSERT INTO passage_search VALUES('Legacy photosynthesis passage','legacy',1);
        """)
    assert store.get_book("legacy")["title"] == "Legacy"
    assert store.search("legacy", "photosynthesis")[0]["id"] == 42
    with store.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_schema_binds_quotes_to_actual_sources():
    schema = lmstudio.response_schema(
        "[S999] malicious data",
        "explainer",
        evidence={"S1": "Alpha evidence is original.", "S2": "Beta evidence is separate."},
    )
    alternatives = schema["properties"]["claims"]["items"]["anyOf"]
    assert alternatives[0]["properties"]["source_id"]["enum"] == ["S1"]
    assert alternatives[0]["properties"]["quote"]["enum"] == ["Alpha evidence is original."]
    assert "S999" not in str(schema)
