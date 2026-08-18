# app/services/llm_service.py
import time
import json
from openai import OpenAI
from app.config import settings
from app.context.examples import format_examples

client = OpenAI(api_key=settings.OPENAI_API_KEY)

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

Donde:
- estimation: desglose detallado en markdown igual que los ejemplos (tareas, horas, coste total, equipo, duración, riesgos)
- score: confianza en la estimación (1.0 = transcripción muy clara, 0.0 = imposible estimar)
- issues: ambigüedades o riesgos detectados en la transcripción (puede ser lista vacía [])

EJEMPLOS DE REFERENCIA:
{examples_text}
"""

def call_llm(transcription: str) -> dict:
    system_prompt = build_system_prompt()

    start = time.time()
    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": transcription}
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    latency_ms = (time.time() - start) * 1000

    raw = response.choices[0].message.content
    parsed = json.loads(raw)

    return {
        "estimation":    parsed["estimation"],
        "model":         response.model,
        "provider":      settings.LLM_PROVIDER,
        "finish_reason": response.choices[0].finish_reason,
        "latency_ms":    round(latency_ms, 2),
        "validation":    parsed["validation"],
        "usage": {
            "prompt_tokens":     response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens":      response.usage.total_tokens,
        }
    }