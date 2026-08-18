# app/routers/estimations.py
from fastapi import APIRouter, HTTPException
from app.schemas.estimation import EstimationRequest, EstimationResponse
from app.services.llm_service import call_llm

router = APIRouter()

@router.post("/estimate", response_model=EstimationResponse)
async def estimate(request: EstimationRequest) -> EstimationResponse:
    try:
        result = call_llm(request.transcription)
        return EstimationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))