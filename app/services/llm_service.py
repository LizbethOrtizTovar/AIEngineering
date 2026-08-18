# app/services/llm_service.py
import time
import json
import os
import structlog
from litellm import completion
from app.config import settings
from app.context.examples import format_examples
from app.services.cache_service import llm_cache

# ── Configuración de structlog ─────────────────────────────────────────────────
def configure_logging():
    import logging
    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.EventRenamer("msg"),
    ]
    if settings.ENV == "production":
        structlog.configure(
            processors=shared_processors + [structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL)
            ),
        )
    else:
        structlog.configure(
            processors=shared_processors + [structlog.dev.ConsoleRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL)
            ),
        )

configure_logging()
logger = structlog.get_logger()

# ── System prompt ──────────────────────────────────────────────────────────────
def build_system_prompt() -> str:
    examples_text = format_examples()
    return f"""Eres un estimador experto en proyectos de software con 15 años de experiencia.

Tu tarea es analizar la transcripción de una reunión con un cliente y generar una estimación
detallada del esfuerzo de desarrollo, siguiendo el mismo formato que los ejemplos de referencia.

REGLAS DE PRICING:
- Tarifa estándar: 50 €/h
- Tarifa senior: 62,50 €/h
- Jornada: 8 horas/día

CONTRATO DE SALIDA — responde SIEMPRE con este JSON y nada más:
{{
  "estimation": "<texto markdown con desglose completo de tareas, horas, costes y riesgos>",
  "validation": {{
    "score": <número entre 0.0 y 1.0>,
    "issues": ["<issue1>", "<issue2>"]
  }}
}}

EJEMPLOS DE REFERENCIA:
{examples_text}
"""

# ── Llamada al LLM con caché ───────────────────────────────────────────────────
def call_llm(transcription: str) -> dict:
    system_prompt = build_system_prompt()
    model = f"{settings.LLM_PROVIDER}/{settings.MODEL_NAME}"

    call_logger = logger.bind(model=model, provider=settings.LLM_PROVIDER)

    # ── Comprobar caché primero ────────────────────────────────────────────────
    cached = llm_cache.get(transcription, model, system_prompt)
    if cached:
        call_logger.info("llm_cache_hit", cache_hit=True)
        return cached

    # ── Cache miss — llamar al LLM ────────────────────────────────────────────
    call_logger.info("llm_call_started")
    start = time.time()

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": transcription}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        latency_ms = round((time.time() - start) * 1000, 2)
        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        call_logger.info(
            "llm_call_completed",
            latency_ms=latency_ms,
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            finish_reason=response.choices[0].finish_reason,
            cache_hit=False,
        )

        result = {
            "estimation":    parsed["estimation"],
            "model":         response.model,
            "provider":      settings.LLM_PROVIDER,
            "finish_reason": response.choices[0].finish_reason,
            "latency_ms":    latency_ms,
            "validation":    parsed["validation"],
            "cache_hit":     False,
            "usage": {
                "prompt_tokens":     response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens":      response.usage.total_tokens,
            }
        }

        # ── Guardar en caché ───────────────────────────────────────────────────
        llm_cache.set(transcription, model, system_prompt, result)
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