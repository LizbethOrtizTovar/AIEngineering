# app/db.py
"""
Conexión a PostgreSQL + pgvector.
Inicializa la extensión y crea la tabla de chunks si no existe.
"""
import structlog
from sqlalchemy import create_engine, text
from app.config import settings

logger = structlog.get_logger()

engine = create_engine(
    settings.POSTGRES_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

INIT_SQL = """
-- Activar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla principal de chunks
CREATE TABLE IF NOT EXISTS embedded_chunks (
    id              SERIAL PRIMARY KEY,
    chunk_id        TEXT UNIQUE NOT NULL,
    text            TEXT NOT NULL,
    embedding       vector(1536),
    budget_id       TEXT,
    component_id    TEXT,
    client_sector   TEXT,
    main_technology TEXT,
    year            INTEGER,
    complexity      TEXT,
    estimated_hours INTEGER,
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para búsqueda aproximada rápida
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON embedded_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Índices de metadata para filtrado
CREATE INDEX IF NOT EXISTS idx_chunks_sector
ON embedded_chunks (client_sector);

CREATE INDEX IF NOT EXISTS idx_chunks_technology
ON embedded_chunks (main_technology);

CREATE INDEX IF NOT EXISTS idx_chunks_year
ON embedded_chunks (year);

CREATE INDEX IF NOT EXISTS idx_chunks_complexity
ON embedded_chunks (complexity);
"""


def init_db() -> None:
    """Crea la extensión pgvector, la tabla y los índices."""
    try:
        with engine.connect() as conn:
            conn.execute(text(INIT_SQL))
            conn.commit()
        logger.info("db_initialized", table="embedded_chunks")
    except Exception as e:
        logger.error("db_init_failed", error=str(e))
        raise


def get_engine():
    return engine