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

## Required API keys / services

- Anthropic API key
- OpenAI API key (embeddings), or swap in a local embedding model
- Cohere API key — only if using hosted rerank instead of the local cross-encoder
- A Nile Postgres project with `pgvector` enabled
