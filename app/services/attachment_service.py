# app/services/attachment_service.py
"""
Camino B: extracción local de texto desde adjuntos.
Independiente del proveedor LLM — prepara el terreno para RAG en módulo 3.
"""
from io import BytesIO
import structlog

logger = structlog.get_logger()


def extract_text_from_pdf(file_bytes: bytes, filename: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(file_bytes))
        parts = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                parts.append(f"--- Página {i} ---\n{text}")
        result = "\n\n".join(parts)
        logger.info("pdf_extracted", filename=filename, pages=len(reader.pages))
        return result
    except Exception as e:
        logger.error("pdf_extraction_failed", filename=filename, error=str(e))
        return f"[Error extrayendo {filename}: {e}]"


def extract_text_from_docx(file_bytes: bytes, filename: str) -> str:
    try:
        from docx import Document
        doc = Document(BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs)
        logger.info("docx_extracted", filename=filename, paragraphs=len(paragraphs))
        return result
    except Exception as e:
        logger.error("docx_extraction_failed", filename=filename, error=str(e))
        return f"[Error extrayendo {filename}: {e}]"


def build_attachments_block(files: list[tuple[str, bytes]]) -> str:
    """
    Recibe lista de (filename, bytes) y devuelve bloque de texto
    listo para inyectar en el prompt con delimitadores claros.
    """
    if not files:
        return ""

    blocks = []
    for filename, content in files:
        name_lower = filename.lower()
        if name_lower.endswith(".pdf"):
            text = extract_text_from_pdf(content, filename)
        elif name_lower.endswith(".docx") or name_lower.endswith(".doc"):
            text = extract_text_from_docx(content, filename)
        else:
            try:
                text = content.decode("utf-8")
            except Exception:
                text = f"[Formato no soportado: {filename}]"

        blocks.append(f"<attachment filename='{filename}'>\n{text}\n</attachment>")

    return "\n\n".join(blocks)