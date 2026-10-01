# app/rag/context_assembler.py
"""
Ensambla los chunks recuperados en un bloque de contexto
ordenado y formateado para el LLM.
"""
import structlog

logger = structlog.get_logger()


def assemble_context(chunks: list[dict]) -> str:
    """
    Convierte una lista de chunks en un bloque de texto
    listo para inyectar en el prompt de generación.
    Ordena por similitud descendente y añade metadatos de citación.
    """
    if not chunks:
        return ""

    # Ordenar por similitud descendente
    sorted_chunks = sorted(
        chunks,
        key=lambda c: c["cosine_similarity"],
        reverse=True
    )

    lines = ["## Presupuestos históricos relevantes\n"]

    for i, chunk in enumerate(sorted_chunks, 1):
        lines.append(f"### Referencia {i} (similitud: {chunk['cosine_similarity']})")
        lines.append(f"**ID:** {chunk['chunk_id']}")
        lines.append(f"**Sector:** {chunk['client_sector']} | "
                     f"**Tecnología:** {chunk['main_technology']} | "
                     f"**Año:** {chunk['year']} | "
                     f"**Complejidad:** {chunk['complexity']}")
        lines.append(f"**Horas estimadas:** {chunk['estimated_hours']}")
        lines.append("")
        lines.append(chunk["text"])
        lines.append("")

    context = "\n".join(lines)

    logger.info(
        "context_assembled",
        chunks_count=len(sorted_chunks),
        context_chars=len(context),
        top_similarity=sorted_chunks[0]["cosine_similarity"] if sorted_chunks else 0,
    )

    return context