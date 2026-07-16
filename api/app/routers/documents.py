from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import get_connection

router = APIRouter(tags=["documents"])


class DocumentStatus(BaseModel):
    id: UUID
    filename: str
    page_count: int | None
    status: str
    error: str | None


@router.get("/documents/{document_id}/status", response_model=DocumentStatus)
async def get_document_status(
    document_id: UUID,
    conn: asyncpg.Connection = Depends(get_connection),
) -> DocumentStatus:
    row = await conn.fetchrow(
        """
        select id, filename, page_count, status, error
        from documents
        where id = $1
        """,
        document_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentStatus(**dict(row))


@router.get("/collections/{collection_id}/documents", response_model=list[DocumentStatus])
async def list_documents(
    collection_id: UUID,
    conn: asyncpg.Connection = Depends(get_connection),
) -> list[DocumentStatus]:
    rows = await conn.fetch(
        """
        select id, filename, page_count, status, error
        from documents
        where collection_id = $1
        order by created_at desc
        """,
        collection_id,
    )
    return [DocumentStatus(**dict(row)) for row in rows]
