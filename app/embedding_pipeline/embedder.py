# app/embedding_pipeline/embedder.py
"""OpenAI embedder with batching and simple exponential retry."""
import time

import structlog
from openai import OpenAI, RateLimitError

from app.embedding_pipeline.schemas import Chunk, EmbeddedChunk

logger = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
RETRY_DELAYS_SECONDS = (1, 2, 4)  # 3 retries on RateLimitError

# ⚠️ PRICE — changes over time. Verify at https://openai.com/api/pricing
# text-embedding-3-small: $0.02 per 1M input tokens (September 2026).
PRICE_PER_MILLION_TOKENS_USD = 0.02


def estimate_cost_usd(total_tokens: int) -> float:
    return round(total_tokens * PRICE_PER_MILLION_TOKENS_USD / 1_000_000, 8)


class OpenAIEmbedder:
    def __init__(self, client: OpenAI | None = None, model: str = EMBEDDING_MODEL, batch_size: int = BATCH_SIZE):
        if client is None:
            from app.config import settings  # lazy: only needed for real calls
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._client = client
        self._model = model
        self._batch_size = batch_size

    def embed_one(self, text: str) -> list[float]:
        return self._create_with_retry([text])[0]

    def embed_many(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        embedded: list[EmbeddedChunk] = []
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start:start + self._batch_size]
            vectors = self._create_with_retry([c.text for c in batch])
            embedded.extend(
                EmbeddedChunk(**c.model_dump(), embedding=v) for c, v in zip(batch, vectors)
            )
        return embedded

    # ── internals ────────────────────────────────────────────────────────────
    def _create_with_retry(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
            try:
                return self._create(texts)
            except RateLimitError:
                if attempt == len(RETRY_DELAYS_SECONDS):
                    logger.error("embedding_rate_limit_exhausted", attempts=attempt + 1)
                    raise
                delay = RETRY_DELAYS_SECONDS[attempt]
                logger.warning("embedding_rate_limited", attempt=attempt + 1, retry_in_s=delay)
                time.sleep(delay)
        raise RuntimeError("unreachable")

    def _create(self, texts: list[str]) -> list[list[float]]:
        start = time.perf_counter()
        response = self._client.embeddings.create(model=self._model, input=texts)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        tokens = response.usage.total_tokens
        logger.info(
            "embedding_batch_completed",
            model=self._model,
            chunks=len(texts),
            tokens=tokens,
            latency_ms=latency_ms,
            cost_usd=estimate_cost_usd(tokens),
        )
        # API returns items with an index; sort to be safe about ordering.
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]
