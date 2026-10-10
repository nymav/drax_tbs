from functools import lru_cache
import os


@lru_cache(maxsize=1)
def model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(os.getenv("DRAX_RERANKER", "cross-encoder/ms-marco-MiniLM-L-6-v2"))


def rerank(query, passages):
    scores = model().predict([(query, p["text"]) for p in passages])
    return [
        {**p, "rerank_score": float(score)}
        for score, p in sorted(zip(scores, passages), key=lambda item: item[0], reverse=True)
    ]
