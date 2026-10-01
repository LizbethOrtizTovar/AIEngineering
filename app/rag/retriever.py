# app/rag/retriever.py
"""
Retriever sobre pgvector con umbral de calidad y soft-fail.
"""
import structlog
import psycopg
from app.config import settings
from app.embedding_pipeline.embedder import OpenAIEmbedder
from functools import lru_cache

logger = structlog.get_logger()

SIMILARITY_THRESHOLD = 0.45  # chunks por debajo de este umbral se descartan
MAX_CHUNKS = 5                # máximo de chunks a recuperar


@lru_cache
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder()


def retrieve(
    search_query: str,
    top_k: int = MAX_CHUNKS,
    filters: dict | None = None,
    threshold: float = SIMILARITY_THRESHOLD,
) -> dict:
    """
    Recupera chunks relevantes para la query.
    Devuelve:
      - chunks: lista de chunks que superan el umbral
      - has_enough_context: bool (True si hay al menos 2 chunks relevantes)
      - retrieval_metadata: métricas del retrieval
    """
    embedder = get_embedder()
    query_vector = embedder.embed_one(search_query)
    query_str = str(query_vector)

    # Construir filtros SQL
    where_clauses = []
    filter_params = []

    if filters:
        if filters.get("client_sector") and filters["client_sector"] != "other":
            where_clauses.append("client_sector = %s")
            filter_params.append(filters["client_sector"])
        if filters.get("main_technology"):
            where_clauses.append("main_technology = %s")
            filter_params.append(filters["main_technology"])
        if filters.get("complexity"):
            where_clauses.append("complexity = %s")
            filter_params.append(filters["complexity"])

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT
            chunk_id,
            text,
            budget_id,
            component_id,
            client_sector,
            main_technology,
            year,
            complexity,
            estimated_hours,
            token_count,
            1 - (embedding <=> %s::vector) AS cosine_similarity
        FROM embedded_chunks
        {where_sql}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    params = tuple([query_str] + filter_params + [query_str, top_k * 2])

    chunks = []
    with psycopg.connect(settings.POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            for row in rows:
                similarity = round(float(row[10]), 4)
                if similarity >= threshold:
                    chunks.append({
                        "chunk_id":          row[0],
                        "text":              row[1],
                        "budget_id":         row[2],
                        "component_id":      row[3],
                        "client_sector":     row[4],
                        "main_technology":   row[5],
                        "year":              row[6],
                        "complexity":        row[7],
                        "estimated_hours":   row[8],
                        "cosine_similarity": similarity,
                    })

    # Limitar al top_k real
    chunks = chunks[:top_k]

    has_enough_context = len(chunks) >= 2
    avg_similarity = round(
        sum(c["cosine_similarity"] for c in chunks) / len(chunks), 4
    ) if chunks else 0.0

    retrieval_metadata = {
        "total_retrieved":    len(chunks),
        "threshold_used":     threshold,
        "avg_similarity":     avg_similarity,
        "has_enough_context": has_enough_context,
        "filters_applied":    filters or {},
    }

    logger.info(
        "retrieval_completed",
        query_chars=len(search_query),
        **retrieval_metadata,
    )

    return {
        "chunks":             chunks,
        "has_enough_context": has_enough_context,
        "retrieval_metadata": retrieval_metadata,
    }