"""Optional exact cosine search for small personal textbook libraries."""

import json
from app.services import store


def query_passages(book_id, query, page_from=None, page_to=None, limit=6):
    from app.services.embedding import get_embeddings

    vector = get_embeddings([query])[0]
    with store.connect() as db:
        rows = db.execute(
            "SELECT id,page,text,vector FROM passages WHERE book_id=? AND vector IS NOT NULL AND (? IS NULL OR page>=?) AND (? IS NULL OR page<=?)",
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
            ranked.append((score, {"id": row["id"], "page": row["page"], "text": row["text"], "score": score}))
    return [row for _, row in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]


def hybrid_search(book_id, query, page_from=None, page_to=None, limit=6):
    """Reciprocal rank fusion followed by a locally hosted cross encoder."""
    lexical = store.search(book_id, query, page_from, page_to, limit=30)
    semantic = query_passages(book_id, query, page_from, page_to, limit=30)
    scores, candidates = {}, {}
    for results in (lexical, semantic):
        for rank, passage in enumerate(results, 1):
            identity = passage["id"]
            scores[identity] = scores.get(identity, 0) + 1 / (60 + rank)
            candidates[identity] = passage
    fused = [candidates[i] for i in sorted(scores, key=scores.get, reverse=True)[:30]]
    if not fused:
        return []
    from app.services.reranker import rerank

    import os

    ranked = rerank(query, fused)
    minimum = ranked[0]["rerank_score"] - float(os.getenv("DRAX_RERANK_SCORE_WINDOW", "3"))
    return [p for p in ranked if p["rerank_score"] >= minimum][:limit]
