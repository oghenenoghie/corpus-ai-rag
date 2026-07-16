import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import RetrievalConfig, settings
from app.retrieval import RetrievedChunk

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

_LOCAL_MODEL_NAME = "BAAI/bge-reranker-base"


@lru_cache(maxsize=1)
def _get_local_model() -> "CrossEncoder":
    # Imported lazily: importing sentence_transformers (and its torch
    # dependency) is expensive, and shouldn't happen at all for anyone
    # running with reranker="cohere".
    from sentence_transformers import CrossEncoder

    return CrossEncoder(_LOCAL_MODEL_NAME)  # type: ignore[no-any-return]


def _rerank_local_sync(query: str, chunks: list[RetrievedChunk]) -> list[float]:
    model = _get_local_model()
    pairs = [(query, chunk.content) for chunk in chunks]
    # sentence-transformers' stub models predict()'s input as a broad
    # multimodal union; list[tuple[str, str]] is the documented text-pair
    # usage for cross-encoders and is correct at runtime.
    scores = model.predict(pairs)  # type: ignore[arg-type]
    return [float(score) for score in scores]


def _rerank_cohere_sync(query: str, chunks: list[RetrievedChunk]) -> list[float]:
    import cohere

    client = cohere.Client(settings.cohere_api_key)
    response = client.rerank(
        model="rerank-v3.5",
        query=query,
        documents=[chunk.content for chunk in chunks],
    )
    scores = [0.0] * len(chunks)
    for result in response.results:
        scores[result.index] = result.relevance_score
    return scores


async def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    config: RetrievalConfig,
) -> list[RetrievedChunk]:
    """Cross-encoder rerank over the fused candidates -> top `rerank_top_k`.
    This is the single biggest quality jump per line of code (see SKILL.md).
    Both backends are blocking calls, so they run in a thread to avoid
    stalling the event loop."""
    if not chunks:
        return []

    if config.reranker == "cohere":
        if not settings.cohere_api_key:
            raise RuntimeError("RetrievalConfig.reranker='cohere' but COHERE_API_KEY is not set")
        scores = await asyncio.to_thread(_rerank_cohere_sync, query, chunks)
    else:
        scores = await asyncio.to_thread(_rerank_local_sync, query, chunks)

    for chunk, score in zip(chunks, scores, strict=True):
        chunk.score = score

    ranked = sorted(chunks, key=lambda c: c.score, reverse=True)
    return ranked[: config.rerank_top_k]
