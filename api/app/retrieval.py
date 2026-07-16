from dataclasses import dataclass, field
from uuid import UUID

import asyncpg

from app.config import RetrievalConfig


@dataclass
class RetrievedChunk:
    id: UUID
    document_id: UUID
    content: str
    page_number: int | None
    heading_path: list[str] = field(default_factory=list)
    score: float = 0.0


async def vector_search(
    conn: asyncpg.Connection,
    collection_id: UUID,
    query_embedding: list[float],
    top_k: int,
) -> list[UUID]:
    """Chunk ids ordered by cosine distance (closest first), via the HNSW
    index on `chunks.embedding`."""
    rows = await conn.fetch(
        """
        select c.id
        from chunks c
        join documents d on d.id = c.document_id
        where d.collection_id = $1
        order by c.embedding <=> $2
        limit $3
        """,
        collection_id,
        query_embedding,
        top_k,
    )
    return [row["id"] for row in rows]


async def keyword_search(
    conn: asyncpg.Connection,
    collection_id: UUID,
    query_text: str,
    top_k: int,
) -> list[UUID]:
    """Chunk ids ordered by ts_rank_cd against the GIN-indexed `tsv` column
    (Postgres full-text search stands in for BM25 here — see SKILL.md)."""
    rows = await conn.fetch(
        """
        select c.id
        from chunks c
        join documents d on d.id = c.document_id
        where d.collection_id = $1
          and c.tsv @@ websearch_to_tsquery('english', $2)
        order by ts_rank_cd(c.tsv, websearch_to_tsquery('english', $2)) desc
        limit $3
        """,
        collection_id,
        query_text,
        top_k,
    )
    return [row["id"] for row in rows]


def reciprocal_rank_fusion(rankings: list[list[UUID]], rrf_k: int) -> list[UUID]:
    """score(d) = sum over rankers 1 / (rrf_k + rank_r(d)), rank 1-indexed.
    Pure function — the eval harness can call this directly to sweep `rrf_k`."""
    scores: dict[UUID, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(scores, key=lambda cid: scores[cid], reverse=True)


async def fetch_chunks(
    conn: asyncpg.Connection,
    chunk_ids: list[UUID],
) -> dict[UUID, RetrievedChunk]:
    if not chunk_ids:
        return {}
    rows = await conn.fetch(
        """
        select id, document_id, content, page_number, heading_path
        from chunks
        where id = any($1::uuid[])
        """,
        chunk_ids,
    )
    return {
        row["id"]: RetrievedChunk(
            id=row["id"],
            document_id=row["document_id"],
            content=row["content"],
            page_number=row["page_number"],
            heading_path=list(row["heading_path"]),
        )
        for row in rows
    }


async def retrieve(
    conn: asyncpg.Connection,
    collection_id: UUID,
    query_embedding: list[float],
    query_text: str,
    config: RetrievalConfig,
) -> list[RetrievedChunk]:
    """Vector + keyword search, fused with RRF, capped to `fused_top_k`.
    Run sequentially, not concurrently — both queries share one asyncpg
    connection, which can't multiplex. Does not rerank; pass the result to
    app.reranker.rerank for the final top `rerank_top_k`."""
    vector_ids = await vector_search(conn, collection_id, query_embedding, config.vector_top_k)
    keyword_ids = await keyword_search(conn, collection_id, query_text, config.keyword_top_k)

    fused_ids = reciprocal_rank_fusion([vector_ids, keyword_ids], config.rrf_k)
    fused_ids = fused_ids[: config.fused_top_k]

    chunks_by_id = await fetch_chunks(conn, fused_ids)
    return [chunks_by_id[cid] for cid in fused_ids if cid in chunks_by_id]
