from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db import get_connection

router = APIRouter(tags=["collections"])


class Collection(BaseModel):
    id: UUID
    name: str
    owner_id: UUID


class CreateCollectionRequest(BaseModel):
    name: str
    owner_id: UUID


@router.get("/collections", response_model=list[Collection])
async def list_collections(
    conn: asyncpg.Connection = Depends(get_connection),
) -> list[Collection]:
    rows = await conn.fetch("select id, name, owner_id from collections order by created_at desc")
    return [Collection(**dict(row)) for row in rows]


@router.post("/collections", response_model=Collection)
async def create_collection(
    request: CreateCollectionRequest,
    conn: asyncpg.Connection = Depends(get_connection),
) -> Collection:
    collection_id = uuid4()
    await conn.execute(
        "insert into collections (id, name, owner_id) values ($1, $2, $3)",
        collection_id,
        request.name,
        request.owner_id,
    )
    return Collection(id=collection_id, name=request.name, owner_id=request.owner_id)
