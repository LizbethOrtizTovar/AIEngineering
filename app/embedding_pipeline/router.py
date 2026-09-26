# app/embedding_pipeline/router.py
from functools import lru_cache

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder, estimate_cost_usd
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse, IngestStats
from app.db import get_engine

logger = structlog.get_logger()
router = APIRouter(tags=["embeddings"])


@lru_cache
def get_chunker() -> JSONStructuralChunker:
    return JSONStructuralChunker()


@lru_cache
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder()


def persist_chunks(embedded: list) -> int:
    """Inserta chunks en PostgreSQL. Devuelve el número de filas insertadas."""
    engine = get_engine()
    inserted = 0

    with engine.connect() as conn:
        for chunk in embedded:
            conn.execute(
                text("""
                    INSERT INTO embedded_chunks (
                        chunk_id, text, embedding,
                        budget_id, component_id, client_sector,
                        main_technology, year, complexity,
                        estimated_hours, token_count
                    ) VALUES (
                        :chunk_id, :text, :embedding,
                        :budget_id, :component_id, :client_sector,
                        :main_technology, :year, :complexity,
                        :estimated_hours, :token_count
                    )
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        text            = EXCLUDED.text,
                        embedding       = EXCLUDED.embedding,
                        client_sector   = EXCLUDED.client_sector,
                        main_technology = EXCLUDED.main_technology,
                        year            = EXCLUDED.year,
                        complexity      = EXCLUDED.complexity,
                        estimated_hours = EXCLUDED.estimated_hours,
                        token_count     = EXCLUDED.token_count
                """),
                {
                    "chunk_id":        chunk.chunk_id,
                    "text":            chunk.text,
                    "embedding":       str(chunk.embedding),
                    "budget_id":       chunk.metadata.get("budget_id"),
                    "component_id":    chunk.metadata.get("component_id"),
                    "client_sector":   chunk.metadata.get("client_sector"),
                    "main_technology": chunk.metadata.get("main_technology"),
                    "year":            chunk.metadata.get("year"),
                    "complexity":      chunk.metadata.get("complexity"),
                    "estimated_hours": chunk.metadata.get("estimated_hours"),
                    "token_count":     chunk.token_count,
                }
            )
            inserted += 1
        conn.commit()

    return inserted


@router.post("/ingest", response_model=IngestResponse)
def ingest(
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

    # Persistir en PostgreSQL
    try:
        inserted = persist_chunks(embedded)
        logger.info("embeddings_persisted", inserted=inserted)
    except Exception as e:
        logger.error("embeddings_persist_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Persist failed: {str(e)}")

    total_tokens = sum(c.token_count for c in embedded)
    stats = IngestStats(
        total_budgets=len(request.budgets),
        total_chunks=len(embedded),
        total_tokens=total_tokens,
        estimated_cost_usd=estimate_cost_usd(total_tokens),
    )
    logger.info("embeddings_ingest_completed", **stats.model_dump())
    return IngestResponse(chunks=embedded, stats=stats)

from app.embedding_pipeline.retrieval import semantic_search
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict | None = None

class SearchResponse(BaseModel):
    results: list[dict]
    total: int


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    try:
        results = semantic_search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )
        return SearchResponse(results=results, total=len(results))
    except Exception as e:
        logger.error("semantic_search_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))