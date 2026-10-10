import io
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from app import config
from app.main import app
from app.services import store, lmstudio
from app.services.pdf_utils import chunk_text


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "workspace.sqlite3")
    monkeypatch.setattr(config, "API_KEY", "")
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(
        lmstudio,
        "ask_local_llm",
        lambda *a, **kw: (_ for _ in ()).throw(lmstudio.ModelUnavailable("Model unavailable for test.")),
    )
    return TestClient(app)


def upload(client, texts=("Page one about photosynthesis and chlorophyll.", "Page two about respiration and glucose.")):
    with fitz.open() as doc:
        for text in texts:
            page = doc.new_page()
            page.insert_text((50, 60), text)
        data = doc.tobytes()
    result = client.post("/api/uploads", files={"file": ("test.pdf", io.BytesIO(data), "application/pdf")})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def indexed(client):
    book = upload(client)
    response = client.post("/api/embed/" + book)
    assert response.status_code == 200, response.text
    return book


def ask(client, book, **extra):
    return client.post("/api/chat/", json={"query": "chlorophyll", "role": "tutor", "pdf_id": book, **extra})


def test_actual_page_sources_and_persisted_history(client):
    book = indexed(client)
    response = ask(client, book)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "evidence"
    assert body["sources"][0]["page"] == 1
    assert "chlorophyll" in body["sources"][0]["text"]
    turns = client.get("/api/sessions/" + body["session_id"]).json()
    assert len(turns) == 1 and turns[0]["response"] == body
    assert len(client.get("/api/sessions", params={"book_id": book}).json()) == 1


def test_document_only_no_match_never_calls_model(client, monkeypatch):
    book = indexed(client)
    monkeypatch.setattr(lmstudio, "ask_local_llm", lambda *a, **kw: pytest.fail("No evidence must not reach model"))
    response = ask(client, book, query="cryptocurrency taxation")
    assert response.json()["mode"] == "no_match"
    assert response.json()["sources"] == []


def test_modes_depth_and_invalid_citations(client, monkeypatch):
    book = indexed(client)
    prompts = []

    def model(prompt, *args, **kwargs):
        prompts.append(prompt)
        return "Explanation [S1]"

    monkeypatch.setattr(lmstudio, "ask_local_llm", model)
    for mode in ["tutor", "explainer", "summarizer", "quizzer", "reviewer"]:
        result = ask(client, book, role=mode, depth="deep").json()
        assert result["mode"] == "generated" and result["role"] == mode
    assert len(set(prompts)) == 5
    monkeypatch.setattr(lmstudio, "ask_local_llm", lambda *a, **kw: "Invented claim [S99]")
    assert ask(client, book).json()["mode"] == "evidence"


def test_session_and_document_scope(client):
    first = indexed(client)
    second = indexed(client)
    session = ask(client, first).json()["session_id"]
    assert ask(client, second, session_id=session).status_code == 400
    assert ask(client, first, page_from=2, page_to=1).status_code == 422
    assert ask(client, first, page_from=3).status_code == 400
    assert ask(client, first, pdf_id="../secrets").status_code == 422
    assert ask(client, first, query=" ").status_code == 422


def test_upload_validation_and_size_cleanup(client, monkeypatch):
    assert client.post("/api/uploads", files={"file": ("x.txt", b"bad")}).status_code == 415
    assert client.post("/api/uploads", files={"file": ("x.pdf", b"bad")}).status_code == 422
    monkeypatch.setattr(config, "MAX_FILE_BYTES", 5)
    assert client.post("/api/uploads", files={"file": ("x.pdf", b"0123456789")}).status_code == 413
    assert not list(config.UPLOAD_DIR.glob("*.pdf"))
    assert client.get("/api/textbooks").json() == []


def test_empty_scanned_document_and_atomic_reindex(client, monkeypatch):
    book = indexed(client)
    before = store.search(book, "chlorophyll")
    with fitz.open() as doc:
        doc.new_page()
        doc.save(config.UPLOAD_DIR / f"{book}.pdf")
    assert client.post("/api/embed/" + book).status_code == 422
    assert store.search(book, "chlorophyll") == before


def test_delete_cascades_document_session_and_index(client):
    book = indexed(client)
    session = ask(client, book).json()["session_id"]
    assert client.delete("/api/textbooks/" + book).status_code == 204
    assert client.get("/api/sessions/" + session).status_code == 404
    assert store.search(book, "chlorophyll") == []
    assert not (config.UPLOAD_DIR / f"{book}.pdf").exists()


def test_workspace_key_and_sample(client, monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "test-key")
    assert client.get("/api/textbooks").status_code == 401
    assert client.get("/api/textbooks", headers={"X-DRAX-Key": "test-key"}).status_code == 200
    assert client.get("/health").status_code == 200
    sample = client.post("/api/sample", headers={"X-DRAX-Key": "test-key"}).json()
    assert sample["pages"] == 3 and sample["status"] == "ready"
    assert store.search(sample["id"], "active recall")


def test_chunking_long_sentences_has_no_empty_or_oversized_chunks():
    chunks = chunk_text("a" * 3000)
    assert all(0 < len(c) <= 1000 for c in chunks)
    assert len(chunks) > 1


def test_model_never_accepts_remote_endpoint(monkeypatch):
    monkeypatch.setattr(config, "LMSTUDIO_API", "https://example.com/v1/chat/completions")
    with pytest.raises(lmstudio.ModelUnavailable):
        lmstudio.local_url()


def test_page_scope_does_not_answer_an_unrelated_question(client, monkeypatch):
    book = indexed(client)
    monkeypatch.setattr(
        lmstudio, "ask_local_llm", lambda *a, **kw: pytest.fail("Unmatched question must not call model")
    )
    result = ask(client, book, query="cryptocurrency taxation", page_from=1, page_to=2)
    assert result.json()["mode"] == "no_match"


def test_local_provider_requires_structured_source_references(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"answer":"A supported point.","source_ids":["S1"]}'},
                    }
                ]
            }

    monkeypatch.setattr(config, "LMSTUDIO_MODEL", "test-model")
    monkeypatch.setattr(config, "LMSTUDIO_API", "http://127.0.0.1:1234/v1/chat/completions")
    monkeypatch.setattr(lmstudio.requests, "post", lambda *a, **kw: Response())
    answer = lmstudio.ask_local_llm("context", "system")
    assert "[S1]" in answer and "A supported point." in answer

    class Invalid(Response):
        def json(self):
            return {"choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"No sources"}'}}]}

    monkeypatch.setattr(lmstudio.requests, "post", lambda *a, **kw: Invalid())
    with pytest.raises(lmstudio.ModelUnavailable):
        lmstudio.ask_local_llm("context", "system")


def test_learning_mode_contracts_reject_missing_questions():
    good = {
        "questions": [
            {"question": "What is active recall?", "answer": "Retrieving an idea before checking notes."}
            for _ in range(3)
        ],
        "source_ids": ["S1"],
    }
    assert "Answer key" in lmstudio.format_response(good, "quizzer")
    with pytest.raises(ValueError):
        lmstudio.format_response({"answer": "Only a statement", "source_ids": ["S1"]}, "quizzer")
    with pytest.raises(ValueError):
        lmstudio.format_response({"answer": "Only an explanation", "source_ids": ["S1"]}, "tutor")
    assert "Your turn:" in lmstudio.format_response(
        {"answer": "Explain a concept.", "source_ids": ["S1"], "next_question": "How would you test recall?"}, "tutor"
    )
