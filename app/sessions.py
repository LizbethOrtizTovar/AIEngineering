# app/sessions.py
"""
Gestión de sesiones conversacionales en memoria del proceso.
Sin persistencia deliberada — aceptamos que las sesiones se pierden
al reiniciar el servicio porque la persistencia pertenece al módulo
de despliegue y producción, no a la fase CAG.
"""
import re
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()

MAX_TURNS = 6

KNOWN_TECHNOLOGIES = {
    "react", "vue", "angular", "nextjs", "nuxt",
    "fastapi", "django", "flask", "rails", "node", "express",
    "postgresql", "mysql", "mongodb", "redis", "sqlite",
    "python", "javascript", "typescript", "golang", "java",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "stripe", "hubspot", "salesforce", "twilio",
}


class ProjectMetadata(BaseModel):
    project_name:           str | None = None
    assumed_team_size:      int | None = None
    mentioned_technologies: list[str]  = Field(default_factory=list)
    agreed_scope:           str | None = None
    explicit_constraints:   list[str]  = Field(default_factory=list)
    rejected_options:       list[str]  = Field(default_factory=list)


class ConversationHistory:
    def __init__(self, max_turns: int = MAX_TURNS):
        self.max_turns = max_turns
        self._turns: list[dict] = []

    def add_turn(self, user: str, assistant: str) -> None:
        self._turns.append({"user": user, "assistant": assistant})
        if len(self._turns) > self.max_turns:
            self._turns = self._turns[-self.max_turns:]

    def to_messages(self, system_prompt: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        for turn in self._turns:
            messages.append({"role": "user",      "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        return messages

    @property
    def turn_count(self) -> int:
        return len(self._turns)


class Session(BaseModel):
    session_id:       str             = Field(default_factory=lambda: str(uuid4()))
    project_metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    created_at:       datetime        = Field(default_factory=datetime.utcnow)
    updated_at:       datetime        = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}
    history: ConversationHistory = Field(
        default_factory=ConversationHistory,
        exclude=True,
    )


_sessions: dict[str, Session] = {}


def create_session() -> Session:
    session = Session()
    _sessions[session.session_id] = session
    logger.info("session_created", session_id=session.session_id)
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def update_metadata_heuristic(
    metadata: ProjectMetadata,
    user_turn: str,
    assistant_turn: str,
) -> ProjectMetadata:
    combined = f"{user_turn}\n{assistant_turn}".lower()
    original = f"{user_turn}\n{assistant_turn}"

    if metadata.project_name is None:
        match = re.search(
            r'(?:se llama|llamado|called|named)\s+["\']?([A-Z][A-Za-z0-9]{2,20})["\']?',
            original
        )
        if match:
            metadata = metadata.model_copy(
                update={"project_name": match.group(1).strip()}
            )

    if metadata.assumed_team_size is None:
        match = re.search(
            r'(\d+)\s*(?:developers?|desarrolladores?|personas?|engineers?)',
            combined
        )
        if match:
            metadata = metadata.model_copy(
                update={"assumed_team_size": int(match.group(1))}
            )

    found = {tech for tech in KNOWN_TECHNOLOGIES if tech in combined}
    if found:
        merged = sorted(set(metadata.mentioned_technologies) | found)
        metadata = metadata.model_copy(update={"mentioned_technologies": merged})

    return metadata