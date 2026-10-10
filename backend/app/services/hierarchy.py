"""Document → outline sections → page passages; extractive staged summaries."""

import json
import re
from app.services import store


def tree(book_id):
    book = store.get_book(book_id)
    with store.connect() as db:
        rows = db.execute("SELECT node FROM hierarchy_nodes WHERE book_id=? ORDER BY ordinal", (book_id,)).fetchall()
    return {"id": "document", "title": book["title"], "sections": [json.loads(r["node"]) for r in rows]}


def build(book, passages):
    outline = next(
        (
            (json.loads(p["structure"]) if isinstance(p.get("structure"), str) else p.get("structure", {})).get(
                "outline"
            )
            for p in passages
            if (json.loads(p["structure"]) if isinstance(p.get("structure"), str) else p.get("structure", {})).get(
                "outline"
            )
        ),
        [],
    )
    entries = [
        (int(level), title, int(page), "pdf-outline")
        for level, title, page, *rest in outline
        if 1 <= int(page) <= book["pages"]
    ]
    if not entries:
        seen = set()
        for p in passages:
            for title in (
                json.loads(p["structure"]) if isinstance(p.get("structure"), str) else p.get("structure", {})
            ).get("headings", []):
                if (p["page"], title) not in seen:
                    entries.append((1, title, p["page"], "inferred-heading"))
                    seen.add((p["page"], title))
    if not entries or entries[0][2] != 1:
        entries.insert(0, (1, "Opening pages", 1, "page-fallback"))
    nodes, parents = [], []
    for i, (level, title, start, origin) in enumerate(entries):
        while parents and parents[-1]["level"] >= level:
            parents.pop()
        end = next(
            (page - 1 for later_level, _, page, _ in entries[i + 1 :] if later_level <= level and page > start),
            book["pages"],
        )
        node = {
            "id": f"section-{i}",
            "title": title,
            "level": level,
            "parent": parents[-1]["id"] if parents else "document",
            "page_from": start,
            "page_to": max(start, end),
            "origin": origin,
        }
        nodes.append(node)
        parents.append(node)
    return {"id": "document", "title": book["title"], "sections": nodes}


def summarize(book_id):
    """Map every indexed passage into a section digest, then assemble a document digest.

    Extractive by design: never treats an earlier generated summary as evidence.
    """
    outline = tree(book_id)
    passages = store.page_passages(book_id, limit=12000)
    mapped = []
    for p in passages:
        if json.loads(p["structure"]).get("kind") == "heading":
            continue
        section = next((n for n in reversed(outline["sections"]) if n["page_from"] <= p["page"] <= n["page_to"]), None)
        sentences = re.split(r"(?<=[.!?])\s+", p["text"])
        mapped.append(
            {
                "passage_id": p["id"],
                "page": p["page"],
                "section": section["id"] if section else "document",
                "quote": sentences[0][:1000],
            }
        )
    sections = [{**node, "notes": [m for m in mapped if m["section"] == node["id"]]} for node in outline["sections"]]
    return {
        "method": "staged-extractive",
        "title": outline["title"],
        "sections": sections,
        "coverage": {"passages": len(passages), "indexed_pages": len({p["page"] for p in passages})},
        "notice": "Opening sentences from every indexed passage, grouped by section. Sparse or scanned pages may have no text. This is an extractive digest, not an AI interpretation.",
    }


def generated_summary(book_id, progress=None):
    """Map bounded batches, then reduce evidenced claims into section summaries."""
    from app.services import lmstudio
    from app.services.rag_agent import SYSTEM

    outline = tree(book_id)
    indexed = store.page_passages(book_id, limit=12000)
    passages = [p for p in indexed if json.loads(p["structure"]).get("kind") != "heading"]
    claims = []
    batches = [passages[i : i + 3] for i in range(0, len(passages), 3)]
    for index, batch in enumerate(batches):
        evidence = {f"S{p['id']}": p["text"] for p in batch}
        prompt = (
            "Summarize the key ideas in these passages in one or two concise claims. Preserve qualifications.\nSources:\n"
            + "\n\n".join(f"[S{p['id']}] Page {p['page']}: {p['text']}" for p in batch)
            + "\nLearner request: Create short source-supported study notes."
        )
        answer = lmstudio.ask_local_llm(prompt, SYSTEM, max_tokens=1200, mode="summarizer", evidence=evidence)
        for claim in answer.claims:
            passage = next(p for p in batch if f"S{p['id']}" == claim["source_id"])
            section = next(
                (n for n in reversed(outline["sections"]) if n["page_from"] <= passage["page"] <= n["page_to"]), None
            )
            claims.append({**claim, "page": passage["page"], "section": section["id"] if section else "document"})
        if progress:
            progress((index + 1) / len(batches))
    # Reduction keeps original claim/quote pairs, removing exact duplicates;
    # generated intermediate prose never becomes a new source of facts.
    unique = {(c["claim"], c["source_id"], c["quote"]): c for c in claims}
    sections = [
        {**node, "claims": [c for c in unique.values() if c["section"] == node["id"]]} for node in outline["sections"]
    ]
    return {
        "method": "staged-evidenced",
        "title": outline["title"],
        "sections": sections,
        "coverage": {
            "indexed_passages": len(indexed),
            "submitted_passages": len(passages),
            "cited_passages": len({c["source_id"] for c in claims}),
            "batches": len(batches),
        },
        "notice": "Every indexed body/table passage was submitted in bounded batches. Summaries may omit details. Exact quotes were checked; semantic correctness still needs review.",
    }
