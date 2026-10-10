"""Optional exact cosine search for small personal textbook libraries."""

import json
from app.services import store


def query_passages(book_id, query, page_from=None, page_to=None, limit=6):
    from app.services.embedding import get_embeddings

    vector = get_embeddings([query])[0]
    with store.connect() as db:
        rows = db.execute(
            "SELECT page,text,vector FROM passages WHERE book_id=? AND vector IS NOT NULL AND (? IS NULL OR page>=?) AND (? IS NULL OR page<=?)",
            (book_id, page_from, page_from, page_to, page_to),
        ).fetchall()
    if not rows:
        raise ValueError("Re-index this document to create semantic vectors.")
    ranked = []
    for row in rows:
        stored = json.loads(row["vector"])
        if len(vector) != len(stored):
            raise ValueError("Embedding model changed. Re-index this document.")
        score = sum(a * b for a, b in zip(vector, stored))
        if score >= 0.35:
            ranked.append((score, {"page": row["page"], "text": row["text"]}))
    return [row for _, row in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]
