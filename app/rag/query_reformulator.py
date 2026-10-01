# app/rag/query_reformulator.py
"""
Reformula una transcripción cruda en campos estructurados
que la búsqueda vectorial puede explotar mejor.
"""
import json
import structlog
from litellm import completion
from app.config import settings

logger = structlog.get_logger()

REFORMULATION_PROMPT = """Analiza esta transcripción de reunión y extrae los campos estructurados.

Responde SOLO con este JSON, sin texto adicional:
{
  "search_query": "<frase corta y precisa para búsqueda semántica, máx 20 palabras>",
  "project_type": "<web_app | mobile_app | api | data_pipeline | internal_tool | other>",
  "client_sector": "<finance | healthcare | retail | education | logistics | other>",
  "main_technology": "<tecnología principal mencionada o null>",
  "complexity": "<low | medium | high | null>",
  "key_components": ["<componente1>", "<componente2>"]
}

Si no hay suficiente información para un campo, usa null.
"""


def reformulate_query(transcription: str) -> dict:
    """
    Extrae campos estructurados de una transcripción.
    Devuelve el dict con search_query y filtros de metadata.
    """
    model = f"{settings.LLM_PROVIDER}/{settings.MODEL_NAME}"

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": REFORMULATION_PROMPT},
                {"role": "user",   "content": f"Transcripción:\n{transcription}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        logger.info(
            "query_reformulated",
            search_query=result.get("search_query"),
            project_type=result.get("project_type"),
            client_sector=result.get("client_sector"),
            main_technology=result.get("main_technology"),
        )

        return result

    except Exception as e:
        logger.error("query_reformulation_failed", error=str(e))
        # Fallback: usar la transcripción truncada como query
        return {
            "search_query": transcription[:200],
            "project_type": None,
            "client_sector": None,
            "main_technology": None,
            "complexity": None,
            "key_components": [],
        }