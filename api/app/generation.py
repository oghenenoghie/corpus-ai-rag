import re
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from anthropic import AsyncAnthropic

from app.config import settings
from app.retrieval import RetrievedChunk

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

_MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You are Corpus, a research assistant that answers questions using only "
    "the numbered context chunks given below the question.\n\n"
    "Rules:\n"
    "- Cite every factual claim with the bracketed chunk number it came "
    "from, immediately after the claim, e.g. [1] or [2][3] for multiple "
    "sources. Use only the chunk numbers listed in the context.\n"
    "- If the context doesn't contain enough information to answer, say so "
    "explicitly instead of guessing. Never answer from your own general "
    "knowledge.\n"
    "- Be concise and directly responsive to the question."
)

# Matches the same "[n]" citation markers the system prompt asks Claude to
# produce. Numbered per-request chunk positions (1..len(chunks)) rather than
# literal chunk UUIDs — asking a model to reproduce a random UUID verbatim
# is unreliable, and the UI renders these as superscript "[1]" anyway (see
# SKILL.md's design system section), so the numbered form is both easier
# for the model and exactly what's needed for display.
_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return f"Context: (nothing retrieved)\n\nQuestion: {question}"
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        heading = " > ".join(chunk.heading_path) if chunk.heading_path else "(no heading)"
        blocks.append(f"[{i}] {heading}\n{chunk.content}")
    context = "\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}"


async def generate_answer(
    conn: asyncpg.Connection,
    conversation_id: UUID,
    question: str,
    chunks: list[RetrievedChunk],
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Streams (event, data) pairs: any number of ("token", {"text": ...}),
    then exactly one ("citations", {...}) and one ("done", {...}). Persists
    the user question and the assistant's answer to `messages`, and each
    resolved [n] marker to `citations`, joining chunk metadata needed for
    the PDF-viewer jump-to-citation UI."""
    prior_rows = await conn.fetch(
        "select role, content from messages where conversation_id = $1 order by created_at asc",
        conversation_id,
    )
    await conn.execute(
        "insert into messages (conversation_id, role, content) values ($1, 'user', $2)",
        conversation_id,
        question,
    )

    anthropic_messages = [
        {"role": row["role"], "content": row["content"]} for row in prior_rows
    ]
    anthropic_messages.append({"role": "user", "content": build_prompt(question, chunks)})

    full_text_parts: list[str] = []
    async with _client.messages.stream(
        model=settings.generation_model,
        max_tokens=_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=anthropic_messages,  # type: ignore[arg-type]
    ) as stream:
        async for delta in stream.text_stream:
            full_text_parts.append(delta)
            yield "token", {"text": delta}

    full_text = "".join(full_text_parts)
    assistant_message_id = uuid4()
    await conn.execute(
        """
        insert into messages (id, conversation_id, role, content)
        values ($1, $2, 'assistant', $3)
        """,
        assistant_message_id,
        conversation_id,
        full_text,
    )

    citations: list[dict[str, Any]] = []
    async with conn.transaction():
        for match in _CITATION_PATTERN.finditer(full_text):
            index = int(match.group(1)) - 1
            if not 0 <= index < len(chunks):
                continue  # model cited a number it wasn't given; skip rather than guess
            chunk = chunks[index]
            await conn.execute(
                """
                insert into citations (message_id, chunk_id, span_start, span_end)
                values ($1, $2, $3, $4)
                """,
                assistant_message_id,
                chunk.id,
                match.start(),
                match.end(),
            )
            citations.append(
                {
                    "marker": index + 1,
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "page_number": chunk.page_number,
                    "span_start": match.start(),
                    "span_end": match.end(),
                }
            )

    yield "citations", {"citations": citations}
    yield "done", {"message_id": str(assistant_message_id)}
