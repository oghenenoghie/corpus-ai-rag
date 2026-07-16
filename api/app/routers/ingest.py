from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from pydantic import BaseModel

from app.db import get_connection

router = APIRouter(tags=["ingest"])


class IngestResponse(BaseModel):
    document_id: UUID
    status: str


async def _run_ingestion_pipeline(document_id: UUID, collection_id: UUID, content: bytes) -> None:
    """Parse -> structure-aware chunk -> embed -> batch insert.

    Phase 1 work (see SKILL.md Build State). Wire up pymupdf parsing,
    the heading-path-aware chunker, and OpenAI embeddings here, updating
    the document's `status` column at each stage.
    """
    raise NotImplementedError


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    collection_id: UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_connection),
) -> IngestResponse:
    document_id = uuid4()
    content = await file.read()

    await conn.execute(
        """
        insert into documents (id, collection_id, filename, status)
        values ($1, $2, $3, 'pending')
        """,
        document_id,
        collection_id,
        file.filename,
    )

    background_tasks.add_task(_run_ingestion_pipeline, document_id, collection_id, content)

    return IngestResponse(document_id=document_id, status="pending")
