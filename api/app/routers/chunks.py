from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import get_connection

router = APIRouter(tags=["chunks"])


class ChunkPreview(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    page_number: int | None
    bbox: dict[str, Any] | None
    heading_path: list[str]


@router.get("/chunks/{chunk_id}", response_model=ChunkPreview)
async def get_chunk(
    chunk_id: UUID,
    conn: asyncpg.Connection = Depends(get_connection),
) -> ChunkPreview:
    row = await conn.fetchrow(
        """
        select id, document_id, content, page_number, bbox, heading_path
        from chunks
        where id = $1
        """,
        chunk_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="chunk not found")
    return ChunkPreview(**dict(row))
