import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import RetrievalConfig, default_retrieval_config
from app.db import get_pool
from app.embeddings import embed_texts
from app.generation import generate_answer
from app.reranker import rerank
from app.retrieval import retrieve

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    conversation_id: UUID
    question: str
    retrieval_config: RetrievalConfig = default_retrieval_config


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_answer(request: QueryRequest) -> AsyncIterator[str]:
    """Retrieve (vector + keyword, fused with RRF) -> rerank -> generate.

    Full pipeline per SKILL.md: embed the question, run vector + keyword
    search fused with RRF, cross-encoder rerank, then stream the Claude
    completion and parse `[n]` citation markers into `citations` rows.
    Acquires its own connection rather than a request-scoped dependency,
    since it needs to outlive the route handler for the life of the stream.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        collection_id = await conn.fetchval(
            "select collection_id from conversations where id = $1",
            request.conversation_id,
        )
        if collection_id is None:
            yield _sse("error", {"detail": "conversation not found"})
            return

        [query_embedding] = await embed_texts([request.question])

        candidates = await retrieve(
            conn,
            collection_id,
            query_embedding,
            request.question,
            request.retrieval_config,
        )
        reranked = await rerank(request.question, candidates, request.retrieval_config)

        yield _sse(
            "retrieval",
            {
                "chunks": [
                    {
                        "id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "page_number": chunk.page_number,
                        "heading_path": chunk.heading_path,
                        "score": chunk.score,
                    }
                    for chunk in reranked
                ]
            },
        )

        async for event, data in generate_answer(
            conn, request.conversation_id, request.question, reranked
        ):
            yield _sse(event, data)


@router.post("/query")
async def query(request: QueryRequest) -> StreamingResponse:
    return StreamingResponse(_stream_answer(request), media_type="text/event-stream")
