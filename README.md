# Corpus — AI Document Intelligence

Ask questions across a document library and get answers with inline, clickable
citations — hybrid retrieval (vector + keyword), a cross-encoder reranker, and
a measured eval suite proving retrieval quality.

Full project context (stack, design system, data model, retrieval pipeline,
eval harness, build state) lives in
[`.claude/skills/corpus-ai-rag/SKILL.md`](.claude/skills/corpus-ai-rag/SKILL.md).

## Stack

- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui — `web/`
- **Backend:** FastAPI (Python) — `api/`
- **DB:** Postgres + pgvector on [Nile](https://www.thenile.dev)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Generation:** Claude API (streaming)
- **Reranking:** `bge-reranker-base` cross-encoder, or Cohere Rerank

## Setup

### 1. Database (Nile)

Run `api/schema.sql` against your Nile Postgres project (`pgvector` must be
enabled — the script creates the extension if missing).

### 2. Backend

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in DATABASE_URL, ANTHROPIC_API_KEY, OPENAI_API_KEY
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd web
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm run dev
```

Visit `/collections`, create one, then open it to drag-and-drop a PDF and
watch ingestion status update live (pending → parsing → embedding → ready).
Open `/collections/[id]/chat` to ask questions; click a citation marker to
open its source PDF at the right page in the pane on the right.

## Status

- **Ingestion (Phase 1):** working end to end — upload → pymupdf parse →
  structure-aware chunking with heading-path prefixing → OpenAI embeddings →
  batch insert, with live status polling in the UI. The original PDF is also
  saved to local disk (`api/storage/`) so it can be served back for viewing.
- **Retrieval (Phase 2):** vector search (HNSW cosine) + keyword search
  (`tsvector`/`ts_rank_cd`) fused with Reciprocal Rank Fusion, then
  cross-encoder reranked (local `bge-reranker-base` by default, or Cohere
  Rerank via `RetrievalConfig.reranker="cohere"`).
- **Answering (Phase 3):** cite-or-abstain prompt template, Claude streaming
  via SSE, `[n]` citation markers parsed out of the stream and persisted to
  `citations` with exact character spans, multi-turn history fed back to
  Claude for follow-ups, and a chat UI with a PDF viewer pane that jumps to
  the cited page on click. **Not implemented:** painting the citation's
  bounding box on the page — the viewer is a native `<iframe>` (page-jump
  only); a highlighted box needs a pdf.js canvas renderer instead.
- **Evals (Phase 4):** not yet implemented — see the Build State checklist
  in the skill doc.

> This project has been developed inside a sandbox with no network path to
> Nile (raw Postgres connections aren't supported through its egress proxy,
> and Nile's HTTPS API isn't allowlisted either) and without a real
> `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`. Everything above is verified with
> `mypy --strict`/`ruff`/`tsc`/`eslint`/`next build`, the Anthropic SDK's
> streaming API was checked against its actual source rather than assumed,
> and the pure-Python pieces (chunker, RRF) are unit-tested directly — but
> nothing has touched the real database or a real model call yet. Run
> `api/schema.sql`, add real API keys, and do a live smoke test (upload a
> PDF, then ask it a question in the chat UI) before trusting this fully.

## Required API keys / services

- Anthropic API key
- OpenAI API key (embeddings), or swap in a local embedding model
- Cohere API key — only if using hosted rerank instead of the local cross-encoder
- A Nile Postgres project with `pgvector` enabled
