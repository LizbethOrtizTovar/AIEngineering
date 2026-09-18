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
    """Llamada simple sin sesión — mantiene compatibilidad con endpoint original."""
    system_prompt, user_prompt = render_estimation_prompt(request, version)
    model = f"{settings.LLM_PROVIDER}/{settings.MODEL_NAME}"

    call_logger = logger.bind(model=model, provider=settings.LLM_PROVIDER)

    cached = llm_cache.get(user_prompt, model, system_prompt)
    if cached:
        call_logger.info("llm_cache_hit", cache_hit=True)
        return cached

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
            "validation":     {"score": 1.0, "issues": []},
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
        call_logger.error("llm_call_failed", error_type=type(e).__name__, error_msg=str(e), latency_ms=latency_ms)
        raise


def call_llm_conversational(request: EstimationRequest, session, attachments_block: str = "", version: str = "v1") -> dict:
    """
    Llamada conversacional con historial y project_metadata.
    Usa ventana deslizante — no cachea porque cada turno es único.
    """
    from app.prompts.loader import render_estimation_prompt
    system_prompt, user_prompt = render_estimation_prompt(request, version)

    # Enriquecer system prompt con project_metadata
    metadata = session.project_metadata
    metadata_lines = []
    if metadata.project_name:
        metadata_lines.append(f"Nombre del proyecto: {metadata.project_name}")
    if metadata.assumed_team_size:
        metadata_lines.append(f"Equipo asumido: {metadata.assumed_team_size} personas")
    if metadata.mentioned_technologies:
        metadata_lines.append(f"Tecnologías mencionadas: {', '.join(metadata.mentioned_technologies)}")
    if metadata.agreed_scope:
        metadata_lines.append(f"Alcance acordado: {metadata.agreed_scope}")
    if metadata.explicit_constraints:
        metadata_lines.append(f"Restricciones: {'; '.join(metadata.explicit_constraints)}")
    if metadata.rejected_options:
        metadata_lines.append(f"Opciones rechazadas: {'; '.join(metadata.rejected_options)}")

    if metadata_lines:
        metadata_block = "\n<project_metadata>\n" + "\n".join(metadata_lines) + "\n</project_metadata>\n"
        system_prompt = system_prompt + metadata_block

    # Añadir adjuntos al user prompt
    if attachments_block:
        user_prompt = f"{user_prompt}\n\n<attachments>\n{attachments_block}\n</attachments>"

    # Construir messages con historial
    messages = session.history.to_messages(system_prompt)
    messages.append({"role": "user", "content": user_prompt})

    model = f"{settings.LLM_PROVIDER}/{settings.MODEL_NAME}"
    call_logger = logger.bind(
        model=model,
        session_id=session.session_id,
        turn=session.history.turn_count + 1,
    )
    call_logger.info("llm_conversational_started")
    start = time.time()

    try:
        response = completion(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        latency_ms = round((time.time() - start) * 1000, 2)
        estimation_text = response.choices[0].message.content

        call_logger.info(
            "llm_conversational_completed",
            latency_ms=latency_ms,
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            turns_in_history=session.history.turn_count,
        )

        return {
            "estimation":     estimation_text,
            "model":          response.model,
            "provider":       settings.LLM_PROVIDER,
            "prompt_version": version,
            "finish_reason":  response.choices[0].finish_reason,
            "latency_ms":     latency_ms,
            "cache_hit":      False,
            "validation":     {"score": 1.0, "issues": []},
            "usage": {
                "prompt_tokens":     response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens":      response.usage.total_tokens,
            }
        }

    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 2)
        call_logger.error("llm_conversational_failed", error_type=type(e).__name__, error_msg=str(e), latency_ms=latency_ms)
        raise