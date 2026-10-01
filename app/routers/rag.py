# app/routers/rag.py
"""
Endpoint RAG que orquesta reformulación, retrieval, ensamblado y generación.
"""
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.rag.query_reformulator import reformulate_query
from app.rag.retriever import retrieve
from app.rag.context_assembler import assemble_context
from app.rag.generator import generate

logger = structlog.get_logger()
router = APIRouter(tags=["rag"])


class RAGRequest(BaseModel):
    transcription: str = Field(min_length=20, max_length=5000)
    top_k: int = 5
    similarity_threshold: float = 0.45
    force_rag: bool = False  # si True, genera aunque no haya contexto suficiente


class RAGResponse(BaseModel):
    estimation:          str
    model:               str
    provider:            str
    latency_ms:          float
    finish_reason:       str
    has_enough_context:  bool
    reformulated_query:  str
    chunks_used:         int
    avg_similarity:      float
    usage:               dict
    sources:             list[dict]


@router.post("/estimate", response_model=RAGResponse)
def rag_estimate(request: RAGRequest) -> RAGResponse:
    """
    Pipeline RAG completo:
    1. Reformula la transcripción en query estructurada
    2. Recupera chunks relevantes de pgvector
    3. Ensambla el contexto
    4. Genera la estimación con grounding
    """
    try:
        # Paso 1 — Reformulación
        reformulated = reformulate_query(request.transcription)

        # Paso 2 — Retrieval con filtros
        filters = {}
        if reformulated.get("client_sector") and reformulated["client_sector"] != "other":
            filters["client_sector"] = reformulated["client_sector"]
        if reformulated.get("main_technology"):
            filters["main_technology"] = reformulated["main_technology"]

        retrieval_result = retrieve(
            search_query=reformulated["search_query"],
            top_k=request.top_k,
            filters=filters if filters else None,
            threshold=request.similarity_threshold,
        )

        # Si los filtros son muy restrictivos y no hay resultados, reintenta sin filtros
        if not retrieval_result["chunks"] and filters:
            logger.info("retry_without_filters", original_filters=filters)
            retrieval_result = retrieve(
                search_query=reformulated["search_query"],
                top_k=request.top_k,
                filters=None,
                threshold=request.similarity_threshold,
            )

        # Paso 3 — Ensamblado del contexto
        context = assemble_context(retrieval_result["chunks"])

        # Paso 4 — Generación
        generation_result = generate(
            transcription=request.transcription,
            context=context,
            has_enough_context=retrieval_result["has_enough_context"],
            reformulated=reformulated,
        )

        # Fuentes citadas
        sources = [
            {
                "chunk_id":          c["chunk_id"],
                "cosine_similarity": c["cosine_similarity"],
                "client_sector":     c["client_sector"],
                "main_technology":   c["main_technology"],
                "estimated_hours":   c["estimated_hours"],
            }
            for c in retrieval_result["chunks"]
        ]

        logger.info(
            "rag_estimate_completed",
            chunks_used=len(retrieval_result["chunks"]),
            has_enough_context=retrieval_result["has_enough_context"],
            avg_similarity=retrieval_result["retrieval_metadata"]["avg_similarity"],
        )

        return RAGResponse(
            estimation=generation_result["estimation"],
            model=generation_result["model"],
            provider=generation_result["provider"],
            latency_ms=generation_result["latency_ms"],
            finish_reason=generation_result["finish_reason"],
            has_enough_context=retrieval_result["has_enough_context"],
            reformulated_query=reformulated["search_query"],
            chunks_used=len(retrieval_result["chunks"]),
            avg_similarity=retrieval_result["retrieval_metadata"]["avg_similarity"],
            usage=generation_result["usage"],
            sources=sources,
        )

    except Exception as e:
        logger.error("rag_estimate_failed", error_type=type(e).__name__, error_msg=str(e))
        raise HTTPException(status_code=500, detail=str(e))