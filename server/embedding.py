from functools import lru_cache
from typing import Generator

from config import get_embedding_client, settings


def _chunk(lst: list, size: int) -> Generator:
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


@lru_cache(maxsize=1)
def _get_local_embedder():
    """Lazy-load local BGE embedder."""
    from langchain_community.embeddings import HuggingFaceBgeEmbeddings
    return HuggingFaceBgeEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
        query_instruction="Represent this sentence for searching relevant passages: ",
    )


def _embed_remote(texts: list[str]) -> list[list[float]] | None:
    """Try remote embedding. Returns None on failure."""
    client = get_embedding_client()
    if client is None or not settings.embedding_api_model:
        return None
    try:
        resp = client.embeddings.create(
            model=settings.embedding_api_model,
            input=texts,
        )
        vectors = [d.embedding for d in resp.data]
        actual_dim = len(vectors[0]) if vectors else 0
        if actual_dim != settings.embedding_dim:
            print(f"[WARN] remote embedding returned {actual_dim}d vectors, but EMBEDDING_DIM={settings.embedding_dim}. Update your .env!")
        return vectors
    except Exception as e:
        print(f"[WARN] remote embedding failed: {e}")
        return None


def _embed_local(texts: list[str], is_query: bool) -> list[list[float]]:
    """Embed via local BGE model."""
    embedder = _get_local_embedder()
    if is_query:
        return [embedder.embed_query(q) for q in texts]
    vectors: list[list[float]] = []
    for batch in _chunk(texts, settings.embedding_batch_size):
        vectors.extend(embedder.embed_documents(batch))
    return vectors


def embed_text(content: str, *, is_query: bool = False) -> list[float]:
    """Embed a single text."""
    return embed_texts([content], is_query=is_query)[0]


def embed_texts(
    contents: list[str],
    *,
    is_query: bool = False,
) -> list[list[float]]:
    """Embed texts — remote first, local fallback."""
    if not contents:
        return []

    if not is_query and settings.embedding_base_url:
        all_vectors: list[list[float]] = []
        for batch in _chunk(contents, settings.embedding_batch_size):
            vectors = _embed_remote(batch)
            if vectors is None:
                raise RuntimeError(
                    f"Remote embedding failed during ingestion. "
                    f"Check EMBEDDING_BASE_URL={settings.embedding_base_url} "
                    f"and EMBEDDING_API_MODEL={settings.embedding_api_model}"
                )
            all_vectors.extend(vectors)
        return all_vectors

    if is_query:
        vectors = _embed_remote(contents)
        if vectors is not None:
            return vectors

    return _embed_local(contents, is_query)
