# streamlit_app.py
import streamlit as st
import requests
from app.config import settings
from app.context.examples import CANONICAL_EXAMPLES
from app.prompts.loader import render_estimation_prompt
from app.schemas.estimation import (
    EstimationRequest, ProjectType, DetailLevel, OutputFormat
)

# ── Configuración ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Estimador CAG",
    page_icon="🧮",
    layout="wide"
)

# ── Session state ─────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = []

if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Panel CAG")

    with st.expander("📋 System prompt activo", expanded=False):
        sample = EstimationRequest(
    transcription="Ejemplo de transcripción para mostrar el system prompt activo.",
            project_type=ProjectType.WEB_SAAS,
            detail_level=DetailLevel.MEDIUM,
            output_format=OutputFormat.PHASES_TABLE,
        )
        system, _ = render_estimation_prompt(sample)
        st.code(system, language="markdown")

    with st.expander("📚 Ejemplos de contexto", expanded=False):
        for i, ex in enumerate(CANONICAL_EXAMPLES, 1):
            st.markdown(f"**Ejemplo {i}**")
            st.caption(ex["meeting_summary"])
            st.divider()

    st.subheader("📊 Última llamada")
    if st.session_state.last_metrics:
        m = st.session_state.last_metrics
        st.metric("Modelo", m["model"])
        st.metric("Tokens entrada", m["prompt_tokens"])
        st.metric("Tokens salida", m["completion_tokens"])
        st.metric("Latencia", f"{m['latency_ms']} ms")
        st.metric("Cache hit", "✅ Sí" if m["cache_hit"] else "❌ No")
        st.metric("Prompt version", m["prompt_version"])
    else:
        st.caption("Aún no hay llamadas realizadas.")

    if st.button("🗑️ Limpiar resultados"):
        st.session_state.results = []
        st.session_state.last_metrics = None
        st.rerun()

# ── Título ────────────────────────────────────────────────────────────────────
st.title("🧮 Estimador de Software CAG")
st.caption("Completa el formulario para obtener una estimación detallada.")

# ── Formulario tipado ─────────────────────────────────────────────────────────
with st.form("estimation_form"):
    transcription = st.text_area(
        "📝 Transcripción de la reunión",
        height=200,
        placeholder="Describe el proyecto o pega la transcripción de la reunión con el cliente...",
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
                "summary":  "📋 Resumen ejecutivo",
                "medium":   "📄 Estándar",
                "detailed": "🔍 Detallado",
            }.get(x, x)
        )

    with col3:
        output_format = st.selectbox(
            "Formato de salida",
            options=[e.value for e in OutputFormat],
            format_func=lambda x: {
                "phases_table": "📅 Fases con tabla",
                "line_items":   "📋 Líneas de trabajo",
                "narrative":    "📖 Narrativa",
            }.get(x, x)
        )

    submitted = st.form_submit_button("🚀 Generar estimación", type="primary")

# ── Llamada a la API ──────────────────────────────────────────────────────────
if submitted:
    if not transcription or len(transcription) < 20:
        st.error("La transcripción debe tener al menos 20 caracteres.")
    else:
        with st.spinner("Generando estimación..."):
            try:
                response = requests.post(
                    "http://localhost:8000/api/v1/estimate",
                    json={
                        "transcription": transcription,
                        "project_type":  project_type,
                        "detail_level":  detail_level,
                        "output_format": output_format,
                    }
                )
                response.raise_for_status()
                data = response.json()

                st.session_state.results.append(data)
                st.session_state.last_metrics = {
                    "model":          data["model"],
                    "prompt_tokens":  data["usage"]["prompt_tokens"],
                    "completion_tokens": data["usage"]["completion_tokens"],
                    "latency_ms":     data["latency_ms"],
                    "cache_hit":      data["cache_hit"],
                    "prompt_version": data["prompt_version"],
                }
                st.rerun()

            except Exception as e:
                st.error(f"Error al llamar a la API: {str(e)}")

# ── Mostrar resultados ────────────────────────────────────────────────────────
for i, result in enumerate(reversed(st.session_state.results), 1):
    with st.expander(f"Estimación #{len(st.session_state.results) - i + 1}", expanded=(i == 1)):
        st.markdown(result["estimation"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Modelo", result["model"])
        col2.metric("Latencia", f"{result['latency_ms']} ms")
        col3.metric("Cache", "✅" if result["cache_hit"] else "❌")