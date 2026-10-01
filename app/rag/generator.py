# app/rag/generator.py
"""
Generación RAG con grounding explícito, política de contexto
insuficiente y citación obligatoria de fuentes.
"""
import time
import structlog
from litellm import completion
from app.config import settings

logger = structlog.get_logger()

GENERATION_SYSTEM_PROMPT = """Eres un experto en estimación de proyectos de software con 15 años de experiencia.

Tu tarea es generar una estimación de esfuerzo basada EXCLUSIVAMENTE en los presupuestos
históricos que se te proporcionan como contexto. No uses conocimiento general — solo el contexto.

REGLAS OBLIGATORIAS:
1. Basa TODA la estimación en los presupuestos históricos del contexto
2. Cita siempre las referencias usadas (ej: "según Referencia 1 [BUD-2023-003::AUTH-001]")
3. Si el contexto no es suficiente para estimar con confianza, di explícitamente:
   "CONTEXTO INSUFICIENTE: No hay suficientes presupuestos históricos similares para
   generar una estimación confiable. Se recomienda [acción específica]."
4. Ajusta la estimación al stack tecnológico y sector del proyecto actual

REGLAS DE PRICING:
- Tarifa estándar: 50 €/h
- Tarifa senior: 62,50 €/h
- Jornada: 8 horas/día

FORMATO DE SALIDA:
## Estimación RAG: [nombre del proyecto]

### Base histórica
[Menciona qué referencias usaste y por qué son relevantes]

### Desglose de tareas
[Tabla con tareas, horas y coste basadas en el contexto histórico]

**Total estimado: X horas**
**Coste estimado: X € (tarifa 50 €/h)**
**Duración estimada: X semanas**

### Ajustes aplicados
[Explica cómo ajustaste las referencias históricas al proyecto actual]

### Referencias citadas
[Lista de chunk_ids usados]
"""


def generate(
    transcription: str,
    context: str,
    has_enough_context: bool,
    reformulated: dict,
) -> dict:
    """
    Genera la estimación usando el contexto recuperado.
    Aplica política de soft-fail si el contexto es insuficiente.
    """
    model = f"{settings.LLM_PROVIDER}/{settings.MODEL_NAME}"

    # Construir user prompt
    if not has_enough_context or not context:
        user_prompt = f"""ADVERTENCIA: El retriever no encontró suficientes presupuestos
históricos similares (umbral mínimo: 2 chunks con similitud >= 0.45).

Transcripción del cliente:
{transcription}

Tipo de proyecto detectado: {reformulated.get('project_type', 'desconocido')}
Sector detectado: {reformulated.get('client_sector', 'desconocido')}

Por favor, indica que el contexto es insuficiente y sugiere qué información
adicional se necesitaría para generar una estimación confiable."""
    else:
        user_prompt = f"""Genera una estimación basada en el contexto histórico proporcionado.

TRANSCRIPCIÓN DEL CLIENTE:
{transcription}

QUERY DE BÚSQUEDA USADA: {reformulated.get('search_query')}
TIPO DE PROYECTO: {reformulated.get('project_type')}
SECTOR: {reformulated.get('client_sector')}

CONTEXTO HISTÓRICO RECUPERADO:
{context}
"""

    start = time.time()

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.2,
        )
        latency_ms = round((time.time() - start) * 1000, 2)
        estimation_text = response.choices[0].message.content

        logger.info(
            "rag_generation_completed",
            latency_ms=latency_ms,
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            has_enough_context=has_enough_context,
            model=response.model,
        )

        return {
            "estimation":    estimation_text,
            "model":         response.model,
            "provider":      settings.LLM_PROVIDER,
            "latency_ms":    latency_ms,
            "finish_reason": response.choices[0].finish_reason,
            "usage": {
                "prompt_tokens":     response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens":      response.usage.total_tokens,
            }
        }

    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 2)
        logger.error(
            "rag_generation_failed",
            error_type=type(e).__name__,
            error_msg=str(e),
            latency_ms=latency_ms,
        )
        raise