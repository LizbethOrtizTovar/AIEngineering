# streamlit_app.py
import streamlit as st
import requests
from app.config import settings
from app.context.examples import CANONICAL_EXAMPLES
from app.prompts.loader import render_estimation_prompt
from app.schemas.estimation import (
    EstimationRequest, ProjectType, DetailLevel, OutputFormat
)

st.set_page_config(page_title="Estimador CAG", page_icon="🧮", layout="wide")

# ── Session state ─────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "results" not in st.session_state:
    st.session_state.results = []
if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None
if "project_metadata" not in st.session_state:
    st.session_state.project_metadata = None

def create_new_session():
    resp = requests.post("http://localhost:8000/api/v1/sessions")
    st.session_state.session_id = resp.json()["session_id"]
    st.session_state.results = []
    st.session_state.last_metrics = None
    st.session_state.project_metadata = None

def refresh_metadata():
    if st.session_state.session_id:
        resp = requests.get(f"http://localhost:8000/api/v1/sessions/{st.session_state.session_id}")
        if resp.status_code == 200:
            st.session_state.project_metadata = resp.json()["project_metadata"]

# Crear sesión inicial
if st.session_state.session_id is None:
    create_new_session()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Panel CAG")

    st.subheader("🔑 Sesión activa")
    st.code(st.session_state.session_id[:8] + "..." if st.session_state.session_id else "Sin sesión")
    st.metric("Turnos", len(st.session_state.results))

    if st.button("🔄 Nueva conversación"):
        create_new_session()
        st.rerun()

    with st.expander("🧠 Memoria del proyecto", expanded=True):
        if st.session_state.project_metadata:
            m = st.session_state.project_metadata
            st.write("**Nombre:**", m.get("project_name") or "—")
            st.write("**Equipo:**", m.get("assumed_team_size") or "—")
            techs = m.get("mentioned_technologies", [])
            st.write("**Tecnologías:**", ", ".join(techs) if techs else "—")
            st.write("**Alcance:**", m.get("agreed_scope") or "—")
        else:
            st.caption("Aún sin datos del proyecto.")

    with st.expander("📊 Última llamada", expanded=False):
        if st.session_state.last_metrics:
            m = st.session_state.last_metrics
            st.metric("Modelo", m["model"])
            st.metric("Tokens entrada", m["prompt_tokens"])
            st.metric("Tokens salida", m["completion_tokens"])
            st.metric("Latencia", f"{m['latency_ms']} ms")
        else:
            st.caption("Aún no hay llamadas.")

    with st.expander("📚 Ejemplos de contexto", expanded=False):
        for i, ex in enumerate(CANONICAL_EXAMPLES, 1):
            st.markdown(f"**Ejemplo {i}**")
            st.caption(ex["meeting_summary"])
            st.divider()

# ── Título ────────────────────────────────────────────────────────────────────
st.title("🧮 Estimador de Software CAG")
st.caption("Conversación multi-turno con memoria del proyecto.")

# ── Formulario ────────────────────────────────────────────────────────────────
with st.form("estimation_form"):
    transcription = st.text_area(
        "📝 Transcripción / mensaje",
        height=150,
        placeholder="Describe el proyecto o añade información nueva...",
    )

    uploaded_files = st.file_uploader(
        "📎 Adjuntos opcionales (PDF, DOCX)",
        type=["pdf", "docx", "doc"],
        accept_multiple_files=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        project_type = st.selectbox(
            "Tipo de proyecto",
            options=[e.value for e in ProjectType],
            format_func=lambda x: {
                "mobile_app":    "📱 App móvil",
                "web_saas":      "🌐 Web / SaaS",
                "internal_tool": "🔧 Herramienta interna",
                "data_pipeline": "📊 Pipeline de datos",
            }.get(x, x)
        )
    with col2:
        detail_level = st.selectbox(
            "Nivel de detalle",
            options=[e.value for e in DetailLevel],
            format_func=lambda x: {
                "summary":  "📋 Resumen",
                "medium":   "📄 Estándar",
                "detailed": "🔍 Detallado",
            }.get(x, x)
        )
    with col3:
        output_format = st.selectbox(
            "Formato",
            options=[e.value for e in OutputFormat],
            format_func=lambda x: {
                "phases_table": "📅 Fases",
                "line_items":   "📋 Líneas",
                "narrative":    "📖 Narrativa",
            }.get(x, x)
        )

    submitted = st.form_submit_button("🚀 Enviar", type="primary")

# ── Llamada a la API ──────────────────────────────────────────────────────────
if submitted:
    if not transcription or len(transcription) < 20:
        st.error("La transcripción debe tener al menos 20 caracteres.")
    else:
        with st.spinner("Generando estimación..."):
            try:
                files = []
                for f in (uploaded_files or []):
                    files.append(("attachments", (f.name, f.read(), f.type)))

                data = {
                    "transcription": transcription,
                    "project_type":  project_type,
                    "detail_level":  detail_level,
                    "output_format": output_format,
                }

                response = requests.post(
                    f"http://localhost:8000/api/v1/sessions/{st.session_state.session_id}/estimate",
                    data=data,
                    files=files if files else None,
                )
                response.raise_for_status()
                result = response.json()

                st.session_state.results.append({
                    "transcription": transcription,
                    "estimation":    result["estimation"],
                    "turn":          len(st.session_state.results) + 1,
                })
                st.session_state.last_metrics = {
                    "model":             result["model"],
                    "prompt_tokens":     result["usage"]["prompt_tokens"],
                    "completion_tokens": result["usage"]["completion_tokens"],
                    "latency_ms":        result["latency_ms"],
                }

                refresh_metadata()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

# ── Historial de turnos ───────────────────────────────────────────────────────
for turn_data in reversed(st.session_state.results):
    with st.expander(f"Turno #{turn_data['turn']}: {turn_data['transcription'][:60]}...", expanded=(turn_data['turn'] == len(st.session_state.results))):
        st.markdown(turn_data["estimation"])