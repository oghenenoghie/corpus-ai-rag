-- Corpus data model (see SKILL.md § Data model).
-- Run against the Nile Postgres database (nile_bronze_brush) after
-- `create extension if not exists vector;` is enabled.

create extension if not exists vector;

create table collections (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_id uuid not null,
    created_at timestamptz not null default now()
);

create table documents (
    id uuid primary key default gen_random_uuid(),
    collection_id uuid not null references collections (id) on delete cascade,
    filename text not null,
    storage_path text,
    page_count int,
    status text not null default 'pending'
        check (status in ('pending', 'parsing', 'embedding', 'ready', 'failed')),
    error text,
    created_at timestamptz not null default now()
);

create table chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents (id) on delete cascade,
    content text not null,
    embedding vector(1536),
    tsv tsvector generated always as (to_tsvector('english', content)) stored,
    page_number int,
    bbox jsonb,
    token_count int,
    chunk_index int not null,
    heading_path text[] not null default '{}'
);

create table conversations (
    id uuid primary key default gen_random_uuid(),
    collection_id uuid not null references collections (id) on delete cascade,
    title text,
    created_at timestamptz not null default now()
);

create table messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations (id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create table citations (
    id uuid primary key default gen_random_uuid(),
    message_id uuid not null references messages (id) on delete cascade,
    chunk_id uuid not null references chunks (id) on delete cascade,
    span_start int not null,
    span_end int not null
);

-- Indexes that matter (HNSW, not IVFFlat — no training step, better recall at these sizes).
create index chunks_embedding_hnsw on chunks using hnsw (embedding vector_cosine_ops);
create index chunks_tsv_gin on chunks using gin (tsv);
