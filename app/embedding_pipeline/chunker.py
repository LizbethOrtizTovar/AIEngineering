# app/embedding_pipeline/chunker.py
"""Structural chunker for historical budget JSON documents.

Strategy (Session 07 pre-exercise): one budget component = one chunk.
The chunk text prepends a contextual header built from the parent budget
(project summary, client sector, year, main technology) so that a generic
component like "Authentication backend" keeps track of where it belongs.
No overlap and no fixed-size splitting on purpose.
"""
from abc import ABC, abstractmethod
from typing import Any

import structlog
import tiktoken

from app.embedding_pipeline.schemas import Budget, BudgetComponent, Chunk

logger = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"
# Not a hard limit (the model accepts 8191 tokens). Chunks above this are
# only flagged in the logs: whether to split them is a discussion for the live session.
LARGE_CHUNK_WARNING_TOKENS = 512


class Chunker(ABC):
    """Common interface for any chunking strategy in the pipeline."""

    @abstractmethod
    def chunk(self, budgets: list[Budget]) -> list[Chunk]:
        """Split documents into a list of Chunk objects."""


class JSONStructuralChunker(Chunker):
    """Chunks budget documents at the component level."""

    def __init__(self, model_for_token_count: str = EMBEDDING_MODEL, tokenizer=None):
        self._tokenizer = tokenizer or tiktoken.encoding_for_model(model_for_token_count)

    def chunk(self, budgets: list[Budget]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for budget in budgets:
            budget_chunks = self._chunk_one_budget(budget)
            logger.info(
                "budget_chunked",
                budget_id=budget.budget_id,
                chunks=len(budget_chunks),
                tokens=sum(c.token_count for c in budget_chunks),
            )
            chunks.extend(budget_chunks)
        return chunks

    # ── internals ────────────────────────────────────────────────────────────
    def _chunk_one_budget(self, budget: Budget) -> list[Chunk]:
        parent_context = self._build_parent_context(budget)
        return [self._build_chunk(c, budget, parent_context) for c in budget.components]

    @staticmethod
    def _build_parent_context(budget: Budget) -> str:
        return (
            f"[Project: {budget.project_summary}]\n"
            f"[Client sector: {budget.client_metadata.sector} | "
            f"Year: {budget.year} | Main tech: {budget.main_technology}]"
        )

    def _build_chunk(self, component: BudgetComponent, budget: Budget, parent_context: str) -> Chunk:
        text = self._render_component_text(component, parent_context)
        token_count = len(self._tokenizer.encode(text))
        chunk_id = f"{budget.budget_id}::{component.component_id}"

        if token_count > LARGE_CHUNK_WARNING_TOKENS:
            logger.warning("large_chunk_detected", chunk_id=chunk_id, token_count=token_count)

        return Chunk(
            chunk_id=chunk_id,
            text=text,
            metadata=self._build_metadata(component, budget),
            token_count=token_count,
        )

    @staticmethod
    def _render_component_text(component: BudgetComponent, parent_context: str) -> str:
        return (
            f"{parent_context}\n\n"
            f"Component: {component.name}\n"
            f"Description: {component.description}\n"
            f"Tech stack: {', '.join(component.tech_stack)}\n"
            f"Complexity: {component.complexity}\n"
            f"Estimated hours: {component.estimated_hours}"
        )

    @staticmethod
    def _build_metadata(component: BudgetComponent, budget: Budget) -> dict[str, Any]:
        """Filterable fields: travel with the chunk but are NOT embedded."""
        return {
            "budget_id": budget.budget_id,
            "component_id": component.component_id,
            "client_sector": budget.client_metadata.sector,
            "main_technology": budget.main_technology,
            "year": budget.year,
            "complexity": component.complexity,
            "estimated_hours": component.estimated_hours,
        }
