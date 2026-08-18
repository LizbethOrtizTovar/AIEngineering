# app/services/llm_service.py
import time
import json
import structlog
from litellm import completion
from app.config import settings
from app.services.cache_service import llm_cache
from app.schemas.estimation import EstimationRequest
from app.prompts.loader import render_estimation_prompt

logger = structlog.get_logger()

def call_llm(request: EstimationRequest, version: str = "v1") -> dict:
    system_prompt, user_prompt = render_estimation_prompt(request, version)
    model = f"{settings.LLM_PROVIDER}/{settings.MODEL_NAME}"

    call_logger = logger.bind(model=model, provider=settings.LLM_PROVIDER)

    # ── Comprobar caché ────────────────────────────────────────────────────────
    cached = llm_cache.get(user_prompt, model, system_prompt)
    if cached:
        call_logger.info("llm_cache_hit", cache_hit=True)
        return cached

    # ── Cache miss — llamar al LLM ─────────────────────────────────────────────
    call_logger.info("llm_call_started")
    start = time.time()

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.2,
        )
        latency_ms = round((time.time() - start) * 1000, 2)
        estimation_text = response.choices[0].message.content

        call_logger.info(
            "llm_call_completed",
            latency_ms=latency_ms,
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            finish_reason=response.choices[0].finish_reason,
            cache_hit=False,
        )

        result = {
            "estimation":     estimation_text,
            "model":          response.model,
            "provider":       settings.LLM_PROVIDER,
            "prompt_version": version,
            "finish_reason":  response.choices[0].finish_reason,
            "latency_ms":     latency_ms,
            "cache_hit":      False,
            "validation": {
                "score":  1.0,
                "issues": []
            },
            "usage": {
                "prompt_tokens":     response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens":      response.usage.total_tokens,
            }
        }

        llm_cache.set(user_prompt, model, system_prompt, result)
        return result

    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 2)
        call_logger.error(
            "llm_call_failed",
            error_type=type(e).__name__,
            error_msg=str(e),
            latency_ms=latency_ms,
        )
        raise