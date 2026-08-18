# app/schemas/estimation.py
from pydantic import BaseModel
from typing import Optional

class EstimationRequest(BaseModel):
    transcription: str
    preprocessing: Optional[str] = "none"

class ValidationResult(BaseModel):
    score: float
    issues: list[str]

class EstimationResponse(BaseModel):
    estimation: str       # texto markdown con desglose detallado
    model: str
    provider: str         # "openai" o "anthropic"
    finish_reason: str
    latency_ms: float
    validation: ValidationResult
    usage: dict