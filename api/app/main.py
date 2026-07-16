from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_pool, get_pool
from app.routers import chunks, collections, documents, ingest, query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="Corpus API", lifespan=lifespan)

app.include_router(collections.router)
app.include_router(ingest.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chunks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
