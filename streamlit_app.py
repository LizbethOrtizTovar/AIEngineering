# streamlit_app.py
import streamlit as st
from openai import OpenAI
from app.config import settings
from app.context.examples import format_examples, CANONICAL_EXAMPLES
from app.services.llm_service import build_system_prompt
import time

# ── Configuración de la página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Estimador CAG",
    page_icon="🧮",
    layout="wide"
)

# ── Cliente OpenAI ────────────────────────────────────────────────────────────
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# ── Session state — historial y métricas ─────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None

# ── NIVEL 3: Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Panel CAG")

    with st.expander("📋 System prompt activo", expanded=False):
        st.code(build_system_prompt(), language="markdown")

    with st.expander("📚 Ejemplos de contexto inyectados", expanded=False):
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
        st.metric("Tiempo de respuesta", f"{m['latency_ms']} ms")
    else:
        st.caption("Aún no hay llamadas realizadas.")

    if st.button("🗑️ Limpiar conversación"):
        st.session_state.messages = []
        st.session_state.last_metrics = None
        st.rerun()

# ── Título principal ──────────────────────────────────────────────────────────
st.title("🧮 Estimador de Software CAG")
st.caption("Pega una transcripción de reunión y obtén una estimación detallada.")

# ── Mostrar historial de mensajes ─────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Input del usuario ─────────────────────────────────────────────────────────
if prompt := st.chat_input("Pega aquí la transcripción de la reunión..."):

    # Añadir mensaje del usuario al historial y mostrarlo
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ── NIVEL 2: Streaming ────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        system_prompt = f"""Eres un estimador experto en proyectos de software con 15 años de experiencia.

Tu tarea es analizar la transcripción de una reunión con un cliente y generar una estimación
detallada del esfuerzo de desarrollo en formato markdown.

REGLAS DE PRICING:
- Tarifa estándar: 50 €/h
- Tarifa senior: 62,50 €/h
- Jornada: 8 horas/día

Responde SIEMPRE en markdown con este formato:
## Estimación: [nombre del proyecto]

### Desglose de tareas:
1. Tarea 1: X horas
2. Tarea 2: X horas

**Total estimado: X horas**
**Coste estimado: X € (tarifa 50 €/h)**
**Equipo recomendado: ...**
**Duración estimada: X semanas**

### Riesgos identificados:
- Riesgo 1
- Riesgo 2

EJEMPLOS DE REFERENCIA:
{format_examples()}
"""

        start = time.time()

        # Sin json_object para que devuelva markdown limpio
        stream = client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": m["role"], "content": m["content"]}
                  for m in st.session_state.messages]
            ],
            stream=True,
            temperature=0.2,
        )

        response_text = st.write_stream(stream)
        latency_ms = round((time.time() - start) * 1000, 2)


    # Guardar respuesta en historial
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text
    })

    # Guardar métricas (aproximadas en streaming)
    prompt_tokens = len(system_prompt.split()) + len(prompt.split())
    completion_tokens = len(response_text.split())
    st.session_state.last_metrics = {
        "model":             settings.MODEL_NAME,
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms":        latency_ms,
    }

    st.rerun()