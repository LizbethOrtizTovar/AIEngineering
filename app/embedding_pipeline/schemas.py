# app/embedding_pipeline/schemas.py
"""Pydantic v2 models for the embedding ingestion pipeline (Session 07)."""
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Closed universe of values present in the historical budgets dataset.
Sector = Literal["finance", "ecommerce", "healthcare", "industrial"]
Complexity = Literal["low", "medium", "high"]


class ClientMetadata(BaseModel):
    name: str = Field(min_length=1)
    sector: Sector
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2")

    @field_validator("country")
    @classmethod
    def country_upper(cls, value: str) -> str:
        return value.upper()


class BudgetComponent(BaseModel):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tech_stack: list[str] = Field(default_factory=list)
    estimated_hours: int = Field(gt=0)
    complexity: Complexity
    dependencies: list[str] = Field(default_factory=list)


class Budget(BaseModel):
    budget_id: str = Field(min_length=1)
    client_metadata: ClientMetadata
    project_summary: str = Field(min_length=1)
    main_technology: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    total_estimated_hours: int = Field(gt=0)
    components: list[BudgetComponent] = Field(min_length=1)

    @field_validator("components")
    @classmethod
    def unique_component_ids(cls, components: list[BudgetComponent]) -> list[BudgetComponent]:
        ids = [c.component_id for c in components]
        if len(ids) != len(set(ids)):
            raise ValueError("component_id values must be unique within a budget")
        return components


class Chunk(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    token_count: int = Field(ge=0)


class EmbeddedChunk(Chunk):
    embedding: list[float]


class IngestRequest(BaseModel):
    budgets: list[Budget] = Field(min_length=1)


class IngestStats(BaseModel):
    total_budgets: int
    total_chunks: int
    total_tokens: int
    estimated_cost_usd: float


class IngestResponse(BaseModel):
    chunks: list[EmbeddedChunk]
    stats: IngestStats
