"""Optional semantic search: no model download at server startup."""

from functools import lru_cache
from app import config


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBEDDING_MODEL)


def get_embeddings(chunks):
    return get_model().encode(chunks, normalize_embeddings=True, convert_to_tensor=False).tolist()
