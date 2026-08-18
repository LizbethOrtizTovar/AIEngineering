# tests/prompts/test_estimation_v1.py
from app.schemas.estimation import (
    EstimationRequest,
    ProjectType,
    DetailLevel,
    OutputFormat,
)
from app.prompts.loader import render_estimation_prompt


def make_request(**kwargs) -> EstimationRequest:
    defaults = {
        "transcription":  "Necesitamos una plataforma web para gestionar pedidos de clientes con panel de administración.",
        "project_type":   ProjectType.WEB_SAAS,
        "detail_level":   DetailLevel.MEDIUM,
        "output_format":  OutputFormat.PHASES_TABLE,
    }
    defaults.update(kwargs)
    return EstimationRequest(**defaults)


# ── Test 1: la transcripción aparece en el user prompt ────────────────────────
def test_user_prompt_contains_transcription():
    request = make_request()
    _, user = render_estimation_prompt(request)
    assert request.transcription in user


# ── Test 2: output_format phases_table incluye confidence_pct ─────────────────
def test_system_phases_table_contains_confidence_pct():
    request = make_request(output_format=OutputFormat.PHASES_TABLE)
    system, _ = render_estimation_prompt(request)
    assert "confidence_pct" in system


# ── Test 3: output_format narrative NO incluye confidence_pct ─────────────────
def test_system_narrative_not_contains_confidence_pct():
    request = make_request(output_format=OutputFormat.NARRATIVE)
    system, _ = render_estimation_prompt(request)
    assert "confidence_pct" not in system


# ── Test 4: detail_level detailed incluye instrucción de asunciones ───────────
def test_system_detailed_contains_assumptions():
    request = make_request(detail_level=DetailLevel.DETAILED)
    system, _ = render_estimation_prompt(request)
    assert "asunciones" in system


# ── Test 5: detail_level summary NO incluye instrucción de asunciones ─────────
def test_system_summary_not_contains_assumptions():
    request = make_request(detail_level=DetailLevel.SUMMARY)
    system, _ = render_estimation_prompt(request)
    assert "asunciones" not in system