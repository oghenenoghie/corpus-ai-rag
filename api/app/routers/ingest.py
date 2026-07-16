from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from pydantic import BaseModel

from app.chunker import chunk_document
from app.config import default_retrieval_config
from app.db import get_connection, get_pool
from app.embeddings import embed_texts
from app.pdf_parser import parse_pdf

router = APIRouter(tags=["ingest"])


class IngestResponse(BaseModel):
    document_id: UUID
    status: str


async def _run_ingestion_pipeline(document_id: UUID, content: bytes) -> None:
    """Parse -> structure-aware chunk -> embed -> batch insert, advancing
    `documents.status` through pending -> parsing -> embedding -> ready
    (or -> failed with the error recorded) at each stage."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "update documents set status = 'parsing' where id = $1", document_id
            )
            parsed = parse_pdf(content)
            drafts = chunk_document(parsed.blocks, default_retrieval_config)

            await conn.execute(
                "update documents set status = 'embedding', page_count = $2 where id = $1",
                document_id,
                parsed.page_count,
            )
            embeddings = await embed_texts([d.embedding_text for d in drafts])

            async with conn.transaction():
                for draft, embedding in zip(drafts, embeddings, strict=True):
                    await conn.execute(
                        """
                        insert into chunks
                            (document_id, content, embedding, page_number, bbox,
                             token_count, chunk_index, heading_path)
                        values ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        document_id,
                        draft.content,
                        embedding,
                        draft.page_number,
                        draft.bbox,
                        draft.token_count,
                        draft.chunk_index,
                        draft.heading_path,
                    )
                await conn.execute(
                    "update documents set status = 'ready' where id = $1", document_id
                )
        except Exception as exc:
            await conn.execute(
                "update documents set status = 'failed', error = $2 where id = $1",
                document_id,
                str(exc),
            )
            raise


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

    background_tasks.add_task(_run_ingestion_pipeline, document_id, content)

    return IngestResponse(document_id=document_id, status="pending")
