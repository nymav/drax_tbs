"""Detect stale indexes without silently mixing embedding spaces."""

import hashlib
import json
from app import config

EXTRACTOR_VERSION = "structured-3"


def fingerprint(book_id, vectors=None):
    path = config.UPLOAD_DIR / f"{book_id}.pdf"
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "extractor": EXTRACTOR_VERSION,
        "embedding": config.EMBEDDING_MODEL if vectors else None,
        "dimension": len(vectors[0]) if vectors else 0,
    }


def stale(book):
    if not book.get("index_version"):
        return True
    saved = json.loads(book["index_version"])
    current = fingerprint(book["id"])
    if config.RETRIEVAL_MODE in {"semantic", "hybrid"} and saved.get("embedding") == config.EMBEDDING_MODEL:
        from app.services.embedding import get_model

        if saved.get("dimension") != get_model().get_sentence_embedding_dimension():
            return True
    return (
        saved["sha256"] != current["sha256"]
        or saved["extractor"] != EXTRACTOR_VERSION
        or (config.RETRIEVAL_MODE in {"semantic", "hybrid"} and saved.get("embedding") != config.EMBEDDING_MODEL)
    )
