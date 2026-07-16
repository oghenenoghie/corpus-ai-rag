from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.db import get_connection
from app.storage import document_file_path

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


@router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: UUID,
    conn: asyncpg.Connection = Depends(get_connection),
) -> FileResponse:
    row = await conn.fetchrow("select filename from documents where id = $1", document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = document_file_path(document_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not stored")
    return FileResponse(path, media_type="application/pdf", filename=row["filename"])
