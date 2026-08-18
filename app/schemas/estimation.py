# app/schemas/estimation.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

# ── Enums para el formulario tipado ───────────────────────────────────────────
class ProjectType(str, Enum):
    MOBILE_APP     = "mobile_app"
    WEB_SAAS       = "web_saas"
    INTERNAL_TOOL  = "internal_tool"
    DATA_PIPELINE  = "data_pipeline"

class DetailLevel(str, Enum):
    SUMMARY  = "summary"
    MEDIUM   = "medium"
    DETAILED = "detailed"

class OutputFormat(str, Enum):
    PHASES_TABLE = "phases_table"
    LINE_ITEMS   = "line_items"
    NARRATIVE    = "narrative"

# ── Request ───────────────────────────────────────────────────────────────────
class EstimationRequest(BaseModel):
    transcription: str = Field(min_length=20, max_length=5000)
    project_type:  ProjectType  = ProjectType.WEB_SAAS
    detail_level:  DetailLevel  = DetailLevel.MEDIUM
    output_format: OutputFormat = OutputFormat.PHASES_TABLE
    preprocessing: Optional[str] = "none"

# ── Response ──────────────────────────────────────────────────────────────────
class ValidationResult(BaseModel):
    score:  float
    issues: list[str]

class EstimationResponse(BaseModel):
    estimation:     str
    model:          str
    provider:       str
    prompt_version: str = "v1"
    finish_reason:  str
    latency_ms:     float
    cache_hit:      bool = False
    validation:     ValidationResult
    usage:          dict