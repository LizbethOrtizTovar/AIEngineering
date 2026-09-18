# tests/test_sessions.py
import pytest
from app.sessions import (
    create_session, get_session,
    update_metadata_heuristic, ProjectMetadata,
    MAX_TURNS
)


# ── Test 1: la metadata se actualiza entre turnos ─────────────────────────────
def test_metadata_updates_across_turns():
    session = create_session()

    # Turno 1 — presentar el proyecto
    session.project_metadata = update_metadata_heuristic(
        metadata=session.project_metadata,
        user_turn="El proyecto se llama BookFlow y usaremos React y PostgreSQL. El equipo es de 3 desarrolladores.",
        assistant_turn="Entendido, estimaré el proyecto BookFlow con React y PostgreSQL para 3 desarrolladores.",
    )

    assert session.project_metadata.project_name is not None
    assert session.project_metadata.assumed_team_size == 3
    assert "react" in session.project_metadata.mentioned_technologies
    assert "postgresql" in session.project_metadata.mentioned_technologies

    # Turno 2 — añadir tecnología nueva
    session.project_metadata = update_metadata_heuristic(
        metadata=session.project_metadata,
        user_turn="Tambien necesitamos Redis para las colas de mensajes.",
        assistant_turn="Añadiré Redis al stack tecnológico.",
    )

    assert "redis" in session.project_metadata.mentioned_technologies
    assert "react" in session.project_metadata.mentioned_technologies  # sigue ahí


# ── Test 2: la ventana deslizante respeta MAX_TURNS ───────────────────────────
def test_sliding_window_respects_max_turns():
    session = create_session()

    # Enviar MAX_TURNS + 2 turnos
    for i in range(MAX_TURNS + 2):
        session.history.add_turn(
            user=f"Turno usuario {i}",
            assistant=f"Turno asistente {i}",
        )

    # El historial no debe superar MAX_TURNS
    assert session.history.turn_count == MAX_TURNS

    # El método to_messages debe tener system + MAX_TURNS pares
    messages = session.history.to_messages("system prompt de prueba")
    expected = 1 + (MAX_TURNS * 2)  # system + (user+assistant) * MAX_TURNS
    assert len(messages) == expected


# ── Test 3: to_messages siempre empieza con system ───────────────────────────
def test_messages_always_starts_with_system():
    session = create_session()

    session.history.add_turn(user="Hola", assistant="Hola, ¿en qué puedo ayudarte?")
    session.history.add_turn(user="Estima esto", assistant="Aquí va la estimación...")

    messages = session.history.to_messages("Eres un experto estimador.")

    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "Eres un experto estimador."
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"