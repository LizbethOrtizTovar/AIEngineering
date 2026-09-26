# app/embedding_pipeline/router.py
from functools import lru_cache

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder, estimate_cost_usd
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse, IngestStats

logger = structlog.get_logger()
router = APIRouter(tags=["embeddings"])


@lru_cache
def get_chunker() -> JSONStructuralChunker:
    return JSONStructuralChunker()


@lru_cache
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder()


@router.post("/ingest", response_model=IngestResponse)
def ingest(  # sync def: FastAPI runs it in a threadpool (blocking OpenAI client)
    request: IngestRequest,
    chunker: JSONStructuralChunker = Depends(get_chunker),
    embedder: OpenAIEmbedder = Depends(get_embedder),
) -> IngestResponse:
    try:
        chunks = chunker.chunk(request.budgets)
        embedded = embedder.embed_many(chunks)
    except Exception as e:
        logger.exception("embeddings_ingest_failed", error_type=type(e).__name__, error_msg=str(e))
        raise HTTPException(status_code=500, detail="Embedding ingestion failed. See service logs.")

    total_tokens = sum(c.token_count for c in embedded)
    stats = IngestStats(
        total_budgets=len(request.budgets),
        total_chunks=len(embedded),
        total_tokens=total_tokens,
        estimated_cost_usd=estimate_cost_usd(total_tokens),
    )
    logger.info("embeddings_ingest_completed", **stats.model_dump())
    return IngestResponse(chunks=embedded, stats=stats)
