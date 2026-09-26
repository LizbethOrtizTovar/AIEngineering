# app/embedding_pipeline/retrieval.py
import structlog
import psycopg
from app.config import settings
from app.embedding_pipeline.embedder import OpenAIEmbedder
from functools import lru_cache

logger = structlog.get_logger()


@lru_cache
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder()


def semantic_search(
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[dict]:
    embedder = get_embedder()
    query_vector = embedder.embed_one(query)
    query_str = str(query_vector)

    # Construir filtros SQL
    where_clauses = []
    filter_params = []

    if filters:
        if filters.get("client_sector"):
            where_clauses.append("client_sector = %s")
            filter_params.append(filters["client_sector"])
        if filters.get("main_technology"):
            where_clauses.append("main_technology = %s")
            filter_params.append(filters["main_technology"])
        if filters.get("year"):
            where_clauses.append("year = %s")
            filter_params.append(filters["year"])
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

    # Construir params: query_vector (para cosine), filtros, query_vector (para order), top_k
    params = tuple([query_str] + filter_params + [query_str, top_k])

    # Conectar directamente con psycopg
    conn_str = settings.POSTGRES_URL.replace("postgresql://", "postgresql://")
    results = []

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            for row in rows:
                results.append({
                    "chunk_id":          row[0],
                    "text":              row[1],
                    "budget_id":         row[2],
                    "component_id":      row[3],
                    "client_sector":     row[4],
                    "main_technology":   row[5],
                    "year":              row[6],
                    "complexity":        row[7],
                    "estimated_hours":   row[8],
                    "cosine_similarity": round(float(row[10]), 4),
                })

    logger.info(
        "semantic_search_completed",
        query_chars=len(query),
        top_k=top_k,
        results_found=len(results),
    )

    return results