# app/prompts/loader.py
import hashlib
import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path
from app.schemas.estimation import EstimationRequest

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent

def render_estimation_prompt(
    request: EstimationRequest,
    version: str = "v1"
) -> tuple[str, str]:
    """
    Renderiza system y user prompt para una EstimationRequest.
    Devuelve (system_prompt, user_prompt).
    """
    env = Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR / "estimation" / version)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    system_template = env.get_template("system.j2")
    user_template   = env.get_template("user.j2")

    context = {"request": request}

    system = system_template.render(**context)
    user   = user_template.render(**context)

    # Log del render con hash para trazabilidad
    system_hash = hashlib.md5(system.encode()).hexdigest()[:8]
    logger.info(
        "prompt_rendered",
        version=version,
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
        system_hash=system_hash,
    )

    return system, user