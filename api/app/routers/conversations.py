from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db import get_connection

router = APIRouter(tags=["conversations"])


class Conversation(BaseModel):
    id: UUID
    collection_id: UUID
    title: str | None


class CreateConversationRequest(BaseModel):
    title: str | None = None


class Citation(BaseModel):
    id: UUID
    chunk_id: UUID
    span_start: int
    span_end: int
    document_id: UUID
    page_number: int | None


class Message(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: str
    citations: list[Citation]


@router.post("/collections/{collection_id}/conversations", response_model=Conversation)
async def create_conversation(
    collection_id: UUID,
    request: CreateConversationRequest,
    conn: asyncpg.Connection = Depends(get_connection),
) -> Conversation:
    conversation_id = uuid4()
    await conn.execute(
        "insert into conversations (id, collection_id, title) values ($1, $2, $3)",
        conversation_id,
        collection_id,
        request.title,
    )
    return Conversation(id=conversation_id, collection_id=collection_id, title=request.title)


@router.get("/collections/{collection_id}/conversations", response_model=list[Conversation])
async def list_conversations(
    collection_id: UUID,
    conn: asyncpg.Connection = Depends(get_connection),
) -> list[Conversation]:
    rows = await conn.fetch(
        """
        select id, collection_id, title
        from conversations
        where collection_id = $1
        order by created_at desc
        """,
        collection_id,
    )
    return [Conversation(**dict(row)) for row in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[Message])
async def list_messages(
    conversation_id: UUID,
    conn: asyncpg.Connection = Depends(get_connection),
) -> list[Message]:
    message_rows = await conn.fetch(
        """
        select id, role, content, created_at
        from messages
        where conversation_id = $1
        order by created_at asc
        """,
        conversation_id,
    )
    if not message_rows:
        return []

    citation_rows = await conn.fetch(
        """
        select ci.id, ci.message_id, ci.chunk_id, ci.span_start, ci.span_end,
               c.document_id, c.page_number
        from citations ci
        join chunks c on c.id = ci.chunk_id
        where ci.message_id = any($1::uuid[])
        """,
        [row["id"] for row in message_rows],
    )
    citations_by_message: dict[UUID, list[Citation]] = {}
    for row in citation_rows:
        citations_by_message.setdefault(row["message_id"], []).append(
            Citation(
                id=row["id"],
                chunk_id=row["chunk_id"],
                span_start=row["span_start"],
                span_end=row["span_end"],
                document_id=row["document_id"],
                page_number=row["page_number"],
            )
        )

    return [
        Message(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"].isoformat(),
            citations=citations_by_message.get(row["id"], []),
        )
        for row in message_rows
    ]
