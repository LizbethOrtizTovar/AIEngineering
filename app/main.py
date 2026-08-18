# app/main.py
from fastapi import FastAPI
from app.routers.estimations import router as estimations_router

app = FastAPI(
    title="Estimador CAG",
    description="API de estimación de software usando Cache Augmented Generation",
    version="0.1.0",
)

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Registrar el router bajo el prefijo /api/v1
app.include_router(estimations_router, prefix="/api/v1")