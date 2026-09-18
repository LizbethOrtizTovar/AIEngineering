# app/routers/estimations.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from app.schemas.estimation import (
    EstimationRequest, EstimationResponse,
    ProjectType, DetailLevel, OutputFormat
)
from app.services.llm_service import call_llm, call_llm_conversational
from app.services.attachment_service import build_attachments_block
from app.sessions import create_session, get_session, update_metadata_heuristic

router = APIRouter()


# ── Endpoint original (sin sesión) ────────────────────────────────────────────
@router.post("/estimate", response_model=EstimationResponse)
async def estimate(request: EstimationRequest) -> EstimationResponse:
    try:
        result = call_llm(request)
        return EstimationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Crear sesión ──────────────────────────────────────────────────────────────
@router.post("/sessions")
async def create_new_session() -> dict:
    session = create_session()
    return {"session_id": session.session_id}


# ── Estimación conversacional con sesión y adjuntos ───────────────────────────
@router.post("/sessions/{session_id}/estimate", response_model=EstimationResponse)
async def estimate_with_session(
    session_id: str,
    transcription: str = Form(...),
    project_type:  str = Form(default="web_saas"),
    detail_level:  str = Form(default="medium"),
    output_format: str = Form(default="phases_table"),
    attachments: list[UploadFile] = File(default=[]),
) -> EstimationResponse:

    # Verificar que la sesión existe
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Sesión {session_id} no encontrada")

    # Procesar adjuntos
    attachment_files = []
    for upload in attachments:
        content = await upload.read()
        attachment_files.append((upload.filename, content))

    attachments_block = build_attachments_block(attachment_files)

    # Construir el request tipado
    request = EstimationRequest(
        transcription=transcription,
        project_type=ProjectType(project_type),
        detail_level=DetailLevel(detail_level),
        output_format=OutputFormat(output_format),
    )

    try:
        result = call_llm_conversational(
            request=request,
            session=session,
            attachments_block=attachments_block,
        )

        # Actualizar historial y metadata
        session.history.add_turn(
            user=transcription,
            assistant=result["estimation"],
        )
        session.project_metadata = update_metadata_heuristic(
            metadata=session.project_metadata,
            user_turn=transcription,
            assistant_turn=result["estimation"],
        )

        return EstimationResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Ver estado de una sesión ──────────────────────────────────────────────────
@router.get("/sessions/{session_id}")
async def get_session_state(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Sesión {session_id} no encontrada")

    return {
        "session_id":       session.session_id,
        "turn_count":       session.history.turn_count,
        "project_metadata": session.project_metadata.model_dump(),
        "created_at":       session.created_at.isoformat(),
    }