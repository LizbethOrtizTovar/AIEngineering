# app/main.py
from fastapi import FastAPI
from app.routers.estimations import router as estimations_router
from app.embedding_pipeline.router import router as embeddings_router
from app.db import init_db
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="Estimador CAG",
    description="API de estimación de software usando Cache Augmented Generation",
    version="0.1.0",
)

@app.on_event("startup")
async def startup():
    try:
        init_db()
        logger.info("startup_complete")
    except Exception as e:
        logger.error("startup_failed", error=str(e))

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Registrar routers
app.include_router(estimations_router, prefix="/api/v1")
app.include_router(embeddings_router, prefix="/embeddings", tags=["embeddings"])