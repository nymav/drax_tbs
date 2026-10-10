import { useEffect, useRef, useState } from "react";
import { request, setWorkspaceKey } from "./api/client";
import { modes, validatePages, sessionMarkdown } from "./lib/study";

function Icon({ name, size = 20 }) {
  const paths = {
    book: (
      <>
        <path d="M4 4h6c2 0 2 2 2 2s0-2 2-2h6v15h-6c-2 0-2 1-2 1s0-1-2-1H4z" />
        <path d="M12 6v14" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="m5 12 14 0m-6-6 6 6-6 6" />,
    upload: (
      <>
        <path d="M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
    download: (
      <>
        <path d="M12 4v12m-5-5 5 5 5-5M4 18v3h16v-3" />
      </>
    ),
    source: (
      <>
        <path d="M5 3h10l4 4v14H5zM15 3v5h4M8 12h8M8 16h6" />
      </>
    ),
    check: <path d="m5 12 4 4 10-10" />,
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.book}
    </svg>
  );
}

function Modal({ children, label, onClose, className = "modal" }) {
  const dialog = useRef(null);
  useEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => element.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className={className}
      aria-label={label}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div>{children}</div>
    </dialog>
  );
}
function Answer({ response }) {
  const index =
    response.role === "quizzer" && response.mode === "generated"
      ? response.answer.search(/(?:^|\n)(?:#{1,6}\s*)?(?:\*\*)?Answer key/i)
      : -1;
  if (index < 0) return <p className="answer">{response.answer}</p>;
  return (
    <>
      <p className="answer">{response.answer.slice(0, index)}</p>
      <details className="answer-key">
        <summary>Check the answer key</summary>
        <p className="answer">{response.answer.slice(index)}</p>
      </details>
    </>
  );
}

const suggestions = [
  "What is the main idea?",
  "Write my own question",
  "Create practice questions",
];
export default function App() {
  const [books, setBooks] = useState([]),
    [book, setBook] = useState(null),
    [status, setStatus] = useState(null);
  const [role, setRole] = useState("tutor"),
    [depth, setDepth] = useState("standard"),
    [query, setQuery] = useState("");
  const [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [turns, setTurns] = useState([]),
    [sessions, setSessions] = useState([]),
    [sessionId, setSessionId] = useState(null);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [loading, setLoading] = useState(true);
  const [help, setHelp] = useState(false),
    [keyPanel, setKeyPanel] = useState(false),
    [key, setKey] = useState(""),
    [pdf, setPdf] = useState(null),
    [dragging, setDragging] = useState(false);
  const [indexJob, setIndexJob] = useState(null);
  const [outline, setOutline] = useState([]), [sectionId, setSectionId] = useState(""), [digest, setDigest] = useState(null);
  const input = useRef(null),
    fileInput = useRef(null),
    abort = useRef(null),
    end = useRef(null);
  const selectedMode = modes.find((m) => m.id === role);
  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [library, health] = await Promise.all([
        request("/textbooks"),
        request("/status"),
      ]);
      setBooks(library);
      setStatus(health);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    refresh();
    return () => abort.current?.abort();
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "nearest",
    });
  }, [turns, busy]);
  async function selectBook(item) {
    if (busy) return;
    setBook(item);
    setOutline([]);
    setSectionId("");
    setDigest(null);
    setTurns([]);
    setSessionId(null);
    setFrom("");
    setTo("");
    setQuery("");
    setError("");
    setNotice("");
    try {
      setSessions(await request(`/sessions?book_id=${item.id}`));
      if (item.status === "ready") setOutline((await request(`/textbooks/${item.id}/hierarchy`)).sections);
    } catch (e) {
      setError(e.message);
    }
  }
  async function indexBook(item) {
    setBusy("Indexing document…");
    try {
      const queued = await request(`/jobs/index/${item.id}`, { method: "POST" });
      setIndexJob(queued.id);
      let job;
      do {
        await new Promise(resolve => setTimeout(resolve, 700));
        job = await request(`/jobs/${queued.id}`);
        setBusy(`Indexing · ${Math.round(job.progress * 100)}% · attempt ${job.attempt}/3`);
      } while (["queued", "running"].includes(job.state));
      if (job.state !== "completed") throw new Error(job.state === "cancelled" ? "Indexing cancelled. Previous index preserved." : job.error);
      const result = JSON.parse(job.result);
      const ready = { ...item, status: "ready" };
      setBooks((old) => old.map((b) => (b.id === item.id ? ready : b)));
      setBook(ready);
      setSectionId("");
      setOutline((await request(`/textbooks/${item.id}/hierarchy`)).sections);
      if (result.sparse_pages.length)
        setNotice(
          `Little or no text on ${result.sparse_pages.length} page(s). Scanned content needs OCR.`,
        );
    } finally {
      setIndexJob(null);
      setBusy("");
    }
  }
  async function summarizeDocument() {
    setBusy("Preparing document notes…"); setError("");
    try {
      const queued = await request(`/jobs/summary/${book.id}`, {method: "POST"});
      setIndexJob(queued.id);
      let job;
      do {
        await new Promise(resolve => setTimeout(resolve, 700));
        job = await request(`/jobs/${queued.id}`);
        setBusy(`Document notes · ${Math.round(job.progress * 100)}% · attempt ${job.attempt}/3`);
      } while (["queued", "running"].includes(job.state));
      if (job.state !== "completed") throw new Error(job.state === "cancelled" ? "Document notes cancelled." : job.error);
      setDigest(JSON.parse(job.result));
    } catch(e) {setError(e.message);}
    finally {setIndexJob(null); setBusy("");}
  }
  async function upload(file) {
    if (!file || busy) return;
    setError("");
    setNotice("");
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF document.");
      return;
    }
    if (file.size > (status?.max_file_mb || 25) * 1024 * 1024) {
      setError(`Use a PDF smaller than ${status?.max_file_mb || 25} MB.`);
      return;
    }
    setBusy("Uploading document…");
    try {
      const data = new FormData();
      data.append("file", file);
      const item = await request("/uploads", { method: "POST", body: data });
      setBooks((old) => [item, ...old.filter(b => b.id !== item.id)]);
      setBook(item);
      setTurns([]);
      setSessionId(null);
      setSessions([]);
      setFrom("");
      setTo("");
      await indexBook(item);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
      if (fileInput.current) fileInput.current.value = "";
    }
  }
  async function sample() {
    setBusy("Opening sample…");
    setError("");
    try {
      const item = await request("/sample", { method: "POST" });
      setBooks((old) => [item, ...old.filter((b) => b.id !== item.id)]);
      setBook(item);
      setOutline((await request(`/textbooks/${item.id}/hierarchy`)).sections);
      setSectionId("");
      setTurns([]);
      setSessions([]);
      setSessionId(null);
      setFrom("");
      setTo("");
      setQuery("What is active recall?");
      setNotice(
        "This sample is a short original study guide. It uses the same indexing and retrieval as your PDFs.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  async function ask(event) {
    event?.preventDefault();
    if (!query.trim() || !book || busy) return;
    const pageError = validatePages(from, to, book.pages);
    if (pageError) {
      setError(pageError);
      return;
    }
    setError("");
    setBusy("Reading the document…");
    const controller = new AbortController();
    abort.current = controller;
    const question = query.trim();
    try {
      const response = await request("/chat/", {
        method: "POST",
        signal: controller.signal,
        body: {
          query: question,
          role,
          depth,
          pdf_id: book.id,
          section_id: sectionId || null,
          session_id: sessionId,
          page_from: from ? Number(from) : null,
          page_to: to ? Number(to) : null,
        },
      });
      setTurns((old) => [...old, { query: question, response }]);
      setSessionId(response.session_id);
      setQuery("");
      setSessions(await request(`/sessions?book_id=${book.id}`));
    } catch (e) {
      if (e.name === "AbortError")
        setNotice(
          "Stopped waiting. The server may still finish and save the turn; reopen the session to check.",
        );
      else setError(e.message);
    } finally {
      abort.current = null;
      setBusy("");
      input.current?.focus();
    }
  }
  async function resume(id) {
    setError("");
    try {
      setTurns(await request(`/sessions/${id}`));
      setSessionId(id);
    } catch (e) {
      setError(e.message);
    }
  }
  async function removeBook() {
    if (
      !book ||
      !window.confirm(
        "Delete this document, its index, and its study sessions from this workspace?",
      )
    )
      return;
    try {
      await request(`/textbooks/${book.id}`, { method: "DELETE" });
      setBooks((old) => old.filter((b) => b.id !== book.id));
      setBook(null);
      setTurns([]);
      setSessions([]);
    } catch (e) {
      setError(e.message);
    }
  }
  function download() {
    const blob = new Blob([sessionMarkdown(book, turns)], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "drax-study-session.md";
    anchor.click();
    URL.revokeObjectURL(url);
  }
  async function openPage(page) {
    try {
      const blob = await request(`/textbooks/${book.id}/pdf`, { raw: true });
      setPdf({ url: URL.createObjectURL(blob), page });
    } catch (e) {
      setError(e.message);
    }
  }
  function closePdf() {
    if (pdf) URL.revokeObjectURL(pdf.url);
    setPdf(null);
  }
  const sources = turns.at(-1)?.response.sources || [];
  return (
    <div className="app-shell">
      <a className="skip" href="#study">
        Skip to study workspace
      </a>
      <header className="topbar">
        <a href="/" className="brand">
          <img src="/mark.svg" alt="" />
          <strong>
            DRAX<span>Textbook study</span>
          </strong>
        </a>
        <div className="top-actions">
          <span className="document-only">
            <Icon name="check" size={15} />
            Document-only
          </span>
          <button onClick={() => setHelp(true)}>How it works</button>
          <button
            onClick={() => setKeyPanel(!keyPanel)}
            aria-expanded={keyPanel}
          >
            Workspace key
          </button>
        </div>
      </header>
      {keyPanel && (
        <form
          className="key-panel"
          onSubmit={(e) => {
            e.preventDefault();
            setWorkspaceKey(key);
            setKeyPanel(false);
            refresh();
          }}
        >
          <label htmlFor="key">Shared workspace key</label>
          <input
            id="key"
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoComplete="off"
          />
          <button className="primary">Connect</button>
          <span>Kept in tab memory only.</span>
        </form>
      )}
      <div className="workspace">
        <aside className="library">
          <div className="section-heading">
            <span className="eyebrow">YOUR LIBRARY</span>
            <button
              className="icon-button"
              aria-label="Upload a PDF"
              disabled={!!busy}
              onClick={() => fileInput.current.click()}
            >
              <Icon name="plus" />
            </button>
          </div>
          <h1>
            Start with
            <br />
            the source.
          </h1>
          <p className="muted">One document. A deeper understanding.</p>
          <input
            ref={fileInput}
            className="visually-hidden"
            type="file"
            accept="application/pdf,.pdf"
            aria-label="Choose a PDF"
            onChange={(e) => upload(e.target.files[0])}
          />
          <button
            className={`upload-zone ${dragging ? "dragging" : ""}`}
            disabled={!!busy}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              upload(e.dataTransfer.files[0]);
            }}
            onClick={() => fileInput.current.click()}
          >
            <Icon name="upload" />
            <strong>Add your PDF</strong>
            <span>Drop a file or browse</span>
            <small>
              Up to {status?.max_file_mb || 25} MB · text-based PDFs
            </small>
          </button>
          <div className="library-heading">
            <span>
              Documents <small>{books.length}</small>
            </span>
            <button onClick={refresh} disabled={loading || !!busy}>
              Refresh
            </button>
          </div>
          {loading ? (
            <p className="muted" role="status">
              Connecting to the workspace…
            </p>
          ) : books.length === 0 ? (
            <p className="empty-library">
              Your library is empty.
              <br />
              Add a PDF or explore the sample.
            </p>
          ) : (
            <ul className="book-list">
              {books.map((item) => (
                <li key={item.id}>
                  <button
                    className={`book ${item.id === book?.id ? "active" : ""}`}
                    disabled={!!busy}
                    onClick={() => selectBook(item)}
                  >
                    <Icon name="book" />
                    <span>
                      <strong>{item.title}</strong>
                      <small>
                        {item.pages} pages ·{" "}
                        {item.status === "ready"
                          ? "Ready to study"
                          : "Needs indexing"}
                      </small>
                    </span>
                    {item.id === book?.id && <span className="book-dot" />}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button
            className="sample-button"
            onClick={sample}
            disabled={!!busy || loading}
          >
            Try a sample document <Icon name="arrow" size={17} />
          </button>
          <div className="library-foot">
            <span
              className={`status-dot ${status?.model_ready ? "ready" : ""}`}
            />
            <span>
              {status?.model_ready
                ? "Local model available"
                : "Source reading available"}
              <small>
                {status?.model_ready
                  ? "Tutoring uses your local model"
                  : "Connect LM Studio for generated tutoring"}
              </small>
            </span>
          </div>
        </aside>
        <main id="study" className="study">
          <div className="study-heading">
            <div>
              <span className="eyebrow">STUDY WORKSPACE</span>
              <h2>{book ? book.title : "Read. Understand. Remember."}</h2>
            </div>
            {book && (
              <button
                className="quiet-button"
                disabled={!!busy}
                onClick={() => openPage(1)}
              >
                <Icon name="source" size={17} />
                Open PDF
              </button>
            )}
          </div>
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <Icon name="close" size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="alert" role="status">
              {notice}
              <button aria-label="Dismiss notice" onClick={() => setNotice("")}>
                <Icon name="close" size={16} />
              </button>
            </div>
          )}
          {!book ? (
            <section className="welcome">
              <span className="welcome-mark">
                <Icon name="book" size={36} />
              </span>
              <p className="eyebrow">LEARN FROM YOUR OWN MATERIAL</p>
              <h3>
                Make the difficult
                <br />
                parts click.
              </h3>
              <p>
                Bring a textbook, course handout, or research paper.
                <br />
                Explore its ideas with explanations you can trace back to the
                page.
              </p>
              <button
                className="primary"
                disabled={!!busy || loading}
                onClick={sample}
              >
                Explore the sample <Icon name="arrow" size={17} />
              </button>
              <div className="welcome-steps">
                <div>
                  <b>01</b>
                  <span>Add a document</span>
                </div>
                <div>
                  <b>02</b>
                  <span>Choose how to learn</span>
                </div>
                <div>
                  <b>03</b>
                  <span>Check the source</span>
                </div>
              </div>
            </section>
          ) : (
            <>
              <section
                className="learning-controls"
                aria-label="Learning settings"
              >
                <div className="mode-tabs" aria-label="Learning mode">
                  {modes.map((mode) => (
                    <button
                      key={mode.id}
                      aria-pressed={role === mode.id}
                      className={role === mode.id ? "selected" : ""}
                      disabled={!!busy}
                      onClick={() => setRole(mode.id)}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
                <div className="scope-controls">
                  <label>
                    Depth
                    <select
                      value={depth}
                      onChange={(e) => setDepth(e.target.value)}
                      disabled={!!busy}
                    >
                      <option value="overview">Quick overview</option>
                      <option value="standard">Standard</option>
                      <option value="deep">Deep dive</option>
                    </select>
                  </label>
                  {outline.length > 0 && <label>Section<select aria-label="Document section" value={sectionId} disabled={!!busy} onChange={e => setSectionId(e.target.value)}><option value="">Whole document</option>{outline.map(node => <option key={node.id} value={node.id}>{node.title} · pp. {node.page_from}–{node.page_to}</option>)}</select></label>}
                  <fieldset>
                    <legend>
                      Page range <span>(optional)</span>
                    </legend>
                    <input
                      type="number"
                      aria-label="Start page"
                      min="1"
                      max={book.pages}
                      value={from}
                      onChange={(e) => setFrom(e.target.value)}
                      placeholder="From"
                      disabled={!!busy}
                    />
                    <span>–</span>
                    <input
                      type="number"
                      aria-label="End page"
                      min="1"
                      max={book.pages}
                      value={to}
                      onChange={(e) => setTo(e.target.value)}
                      placeholder="To"
                      disabled={!!busy}
                    />
                  </fieldset>
                </div>
              </section>
              {(book.status !== "ready" || book.index_stale) && (
                <div className="alert">
                  This PDF needs a current index.
                  <button
                    disabled={!!busy}
                    onClick={() =>
                      indexBook(book).catch((e) => setError(e.message))
                    }
                  >
                    Index document
                  </button>
                </div>
              )}
              <div className="session-bar">
                <label className="visually-hidden" htmlFor="session">
                  Study session
                </label>
                <select
                  id="session"
                  value={sessionId || ""}
                  disabled={!!busy}
                  onChange={(e) =>
                    e.target.value
                      ? resume(e.target.value)
                      : (setTurns([]), setSessionId(null))
                  }
                >
                  <option value="">New study session</option>
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
                <button
                  disabled={!!busy}
                  onClick={() => {
                    setTurns([]);
                    setSessionId(null);
                    setQuery("");
                  }}
                >
                  New session
                </button>
                <button disabled={!turns.length || !!busy} onClick={download}>
                  <Icon name="download" size={15} />
                  Export
                </button>
              </div>
              <div
                className="conversation"
                role="log"
                aria-label="Study conversation"
                aria-live="polite"
              >
                {turns.length === 0 ? (
                  <div className="conversation-empty">
                    <span className="eyebrow">{selectedMode.label}</span>
                    <h3>
                      {role === "reviewer"
                        ? "Put your understanding to the test."
                        : "What would you like to understand?"}
                    </h3>
                    <p>
                      {selectedMode.description} Use a topic from the document
                      or select pages to focus on.
                    </p>
                    <div className="suggestions">
                      {(role === "summarizer"
                        ? ["Summarize this document"]
                        : role === "reviewer"
                          ? ["My understanding is…"]
                          : suggestions
                      ).map((s) => (
                        <button
                          key={s}
                          disabled={!!busy}
                          onClick={() => {
                            setQuery(s === "Write my own question" ? "" : s);
                            if (s === "Create practice questions")
                              setRole("quizzer");
                            input.current?.focus();
                          }}
                        >
                          {s}
                          <Icon name="arrow" size={14} />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  turns.map((turn, i) => (
                    <article className="turn" key={i}>
                      <div className="learner-question">
                        <span>You</span>
                        <p>{turn.query}</p>
                      </div>
                      <div className="response">
                        <div className="response-heading">
                          <img src="/mark.svg" alt="" />
                          <strong>DRAX</strong>
                          <span
                            className={`response-mode ${turn.response.mode}`}
                          >
                            {turn.response.mode === "generated"
                              ? "Model-generated"
                              : turn.response.mode === "evidence"
                                ? "Source passages"
                                : "No match"}
                          </span>
                          <small>
                            {
                              modes.find((m) => m.id === turn.response.role)
                                ?.label
                            }{" "}
                            · {turn.response.depth}
                          </small>
                        </div>
                        <Answer response={turn.response} />
                        {turn.response.notice && (
                          <p className="response-notice">
                            {turn.response.notice}
                          </p>
                        )}
                        {turn.response.sources?.length > 0 && (
                          <details className="inline-sources">
                            <summary>
                              {turn.response.sources.length} retrieved passages
                              · inspect evidence
                            </summary>
                            {turn.response.sources.map((source) => (
                              <div className="source-excerpt" key={source.id}>
                                <button onClick={() => openPage(source.page)}>
                                  [{source.id}] Page {source.page} ↗
                                </button>
                                <p>{source.text}</p>
                              </div>
                            ))}
                          </details>
                        )}
                      </div>
                    </article>
                  ))
                )}
                {busy && (
                  <div role="status" className="working">
                    <span className="spinner" />
                    {busy}
                  </div>
                )}
                <div ref={end} />
              </div>
              <form className="composer" onSubmit={ask}>
                <label className="visually-hidden" htmlFor="question">
                  Ask about this document
                </label>
                <textarea
                  ref={input}
                  id="question"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  maxLength={4000}
                  placeholder={
                    role === "reviewer"
                      ? "Write your explanation here. DRAX will compare it with the document."
                      : "Ask about a concept, or choose a page range…"
                  }
                  rows="3"
                  disabled={!!busy || book.status !== "ready"}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey &&
                      !e.nativeEvent.isComposing
                    ) {
                      e.preventDefault();
                      ask();
                    }
                  }}
                />
                <div className="composer-footer">
                  <small>
                    Document only · Enter to send · Shift + Enter for a new line
                  </small>
                  {abort.current ? (
                    <button
                      type="button"
                      onClick={() => abort.current?.abort()}
                    >
                      Stop waiting
                    </button>
                  ) : (
                    <button
                      className="primary"
                      disabled={
                        !query.trim() || !!busy || book.status !== "ready"
                      }
                    >
                      Ask DRAX <Icon name="arrow" size={17} />
                    </button>
                  )}
                </div>
              </form>
              <p className="disclaimer">
                Generated explanations can be incorrect. Check the original page
                before relying on an answer.
              </p>
            </>
          )}
        </main>
        {book && (
          <aside className="evidence-panel">
            <span className="eyebrow">SOURCE DESK</span>
            <h3>
              Keep the evidence
              <br />
              in view.
            </h3>
            <div className="document-meta">
              <Icon name="book" size={26} />
              <strong>{book.title}</strong>
              <span>
                {book.pages} pages · {book.author}
              </span>
              <span>
                {status?.retrieval === "hybrid" ? "Hybrid + reranking" : status?.retrieval === "semantic"
                  ? "Semantic retrieval"
                  : "Keyword retrieval"}
              </span>
            </div>
            {sources.length ? (
              <div className="source-list">
                {sources.map((source) => (
                  <details key={source.id}>
                    <summary>
                      <span>{source.id}</span>Page {source.page}
                      <Icon name="plus" size={14} />
                    </summary>
                    <p>{source.text}</p>
                    <button onClick={() => openPage(source.page)}>
                      View original page ↗
                    </button>
                  </details>
                ))}
              </div>
            ) : (
              <p className="muted">
                Retrieved passages will appear here after your first question.
              </p>
            )}
            <div className="scope-note">
              <strong>The boundary is your document.</strong>
              <p>
                DRAX searches this PDF only. It does not browse the web or
                silently answer from general knowledge.
              </p>
            </div>
            <button className="quiet-button" disabled={!!busy || book.status !== "ready"} onClick={() => request(`/textbooks/${book.id}/digest`).then(setDigest).catch(e => setError(e.message))}>Read section digest</button>
            <button className="quiet-button" disabled={!!busy || !status?.model_ready || book.status !== "ready"} onClick={summarizeDocument}>Generate full-document notes</button>
            {indexJob && <button className="quiet-button" onClick={() => request(`/jobs/${indexJob}/cancel`, {method: "POST"}).catch(e => setError(e.message))}>Cancel job</button>}
            <button className="quiet-button" disabled={!!busy} onClick={() => indexBook(book).catch(e => setError(e.message))}>Re-index document</button>
            <button
              className="delete-button"
              onClick={removeBook}
              disabled={!!busy}
            >
              Delete document & sessions
            </button>
          </aside>
        )}
      </div>
      {digest && <Modal label="Document section digest" onClose={() => setDigest(null)}><button className="modal-close" aria-label="Close digest" onClick={() => setDigest(null)} autoFocus><Icon name="close" /></button><p className="eyebrow">DOCUMENT DIGEST</p><h2>{digest.title}</h2><p>{digest.notice}</p><p>{digest.coverage.passages ?? digest.coverage.submitted_passages} passages processed</p>{digest.sections.map(section => <section key={section.id}><h3>{section.title}</h3>{(section.notes || section.claims || []).map((note, index) => <blockquote key={note.passage_id || index}>{note.claim && <p>{note.claim}</p>}{note.quote}<br/><button className="quiet-button" onClick={() => {setDigest(null); openPage(note.page);}}>Page {note.page} ↗</button></blockquote>)}</section>)}</Modal>}
      {help && (
        <Modal label="How to use DRAX" onClose={() => setHelp(false)}>
          <button
            className="modal-close"
            aria-label="Close help"
            onClick={() => setHelp(false)}
            autoFocus
          >
            <Icon name="close" />
          </button>
          <p className="eyebrow">A SMALL STUDY GUIDE</p>
          <h2 id="help-title">Learn with the source open.</h2>
          <ol>
            <li>Add a text-based PDF. Scanned pages require OCR first.</li>
            <li>
              Choose guided learning, explanations, study notes, practice, or
              answer review.
            </li>
            <li>
              Ask using the document’s terminology. Page ranges focus on the
              first retrieved passages in that range.
            </li>
            <li>
              Inspect source cards and open the original page. Model citations
              are references, not a guarantee of correctness.
            </li>
            <li>
              Resume sessions from the menu or export your notes as Markdown.
            </li>
          </ol>
          <p>
            Files, extracted passages, and sessions are stored on the backend
            machine. Local model calls stay on that machine. There are no
            analytics. This is a personal/shared workspace, not separate private
            accounts.
          </p>
          <p>
            Without LM Studio, DRAX shows real retrieved passages, not simulated
            tutoring.
          </p>
        </Modal>
      )}
      {pdf && (
        <Modal label="Original PDF" className="pdf-modal" onClose={closePdf}>
          <div>
            <strong>Original document · page {pdf.page}</strong>
            <button aria-label="Close PDF" onClick={closePdf} autoFocus>
              <Icon name="close" />
            </button>
          </div>
          <iframe
            title="Original PDF"
            src={`${pdf.url}#page=${pdf.page}`}
            referrerPolicy="no-referrer"
          />
          <a href={pdf.url} target="_blank" rel="noreferrer">
            Open PDF in a new tab
          </a>
        </Modal>
      )}
    </div>
  );
}
