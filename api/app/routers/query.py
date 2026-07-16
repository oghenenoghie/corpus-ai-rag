from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import RetrievalConfig, default_retrieval_config

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    conversation_id: UUID
    question: str
    retrieval_config: RetrievalConfig = default_retrieval_config


async def _stream_answer(request: QueryRequest) -> AsyncIterator[str]:
    """Retrieve (vector + keyword, fused with RRF) -> rerank -> generate.

    Phase 2/3 work (see SKILL.md Build State):
      1. vector_search + keyword_search against `chunks`, fused with RRF
      2. cross-encoder rerank down to `retrieval_config.rerank_top_k`
      3. stream the Claude completion, parsing `[chunk_id]` citation markers
         into SSE `citation` events as they resolve
    Each yielded string must be a valid SSE frame, e.g. f"data: {json}\\n\\n".
    """
    raise NotImplementedError
    yield ""  # pragma: no cover - keeps this an async generator until implemented


@router.post("/query")
async def query(request: QueryRequest) -> StreamingResponse:
    return StreamingResponse(_stream_answer(request), media_type="text/event-stream")
