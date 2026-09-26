# Estimador de Software CAG

Servicio de estimación de proyectos de software usando arquitectura **CAG (Cache Augmented Generation)**.
Construido con FastAPI + Streamlit + LiteLLM + Redis.

---

## Cómo levantar el proyecto

### Requisitos
- Python 3.11+
- uv (gestor de paquetes)
- Docker Desktop (para Redis)
- API key de OpenAI y/o Anthropic en `.env`

### Arrancar
```powershell
# Terminal 1 — Redis
docker start redis-estimador

# Terminal 2 — FastAPI
uv run uvicorn app.main:app --reload

# Terminal 3 — Streamlit
uv run streamlit run streamlit_app.py
```

### Ejecutar tests
```powershell
uv run pytest tests/ -v
```

### URLs
| Servicio | URL |
|----------|-----|
| API REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Streamlit | http://localhost:8501 |

---

## Variables de entorno (.env)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
ENV=development

---

## Sesiones completadas

### ✅ Sesión 02 — Arquitectura CAG base
**Qué construimos:** Primera versión del estimador con arquitectura CAG.

**Archivos clave:**
- `app/context/examples.py` — Ejemplos canónicos few-shot (el "conocimiento" del sistema)
- `app/services/llm_service.py` — Llamada al LLM con system prompt + ejemplos
- `app/schemas/estimation.py` — Schemas de entrada y salida
- `app/routers/estimations.py` — Endpoint `POST /api/v1/estimate`
- `app/main.py` — FastAPI con health check

**Lo que aprendimos:**
- CAG = inyectar ejemplos estáticos en el prompt (sin base de datos, sin retrieval)
- Separación de responsabilidades: routers / services / context / schemas
- Documentación automática con Swagger en `/docs`

---

### ✅ Sesión 03 — Abstracción de proveedores + Caché + Logging
**Qué construimos:** Capa de infraestructura sobre el estimador base.

**Archivos clave:**
- `app/services/llm_service.py` — Refactorizado con LiteLLM
- `app/services/cache_service.py` — Cacheo exact-match con Redis
- `streamlit_app.py` — Interfaz conversacional con streaming

**Lo que aprendimos:**
- **LiteLLM** desacopla el código del proveedor — cambiar de OpenAI a Anthropic es un cambio de configuración, no de código
- **Redis** cachea respuestas idénticas — la segunda llamada con el mismo input no llega al LLM
- **Structlog** emite logs estructurados con timestamps y campos tipados
- **Streaming** con `st.write_stream` — el usuario ve la respuesta token a token

**Decisiones arquitectónicas:**
- Cacheo exact-match (no semántico) porque las transcripciones largas tienen alta probabilidad de match exacto
- LiteLLM como librería (no como proxy) para minimizar infraestructura

---

### ✅ Sesión 04 — Templates Jinja2 + Formulario tipado + Tests
**Qué construimos:** Sacar el prompt del código a templates versionados y reemplazar el chat libre por un formulario tipado.

**Archivos clave:**
- `app/prompts/estimation/v1/system.j2` — System prompt con condicionales por nivel de detalle y formato
- `app/prompts/estimation/v1/user.j2` — User prompt con datos del proyecto
- `app/prompts/estimation/v1/examples.j2` — Ejemplos few-shot en template
- `app/prompts/loader.py` — Renderiza templates y emite log con hash para trazabilidad
- `app/schemas/estimation.py` — Enums tipados: `ProjectType`, `DetailLevel`, `OutputFormat`
- `tests/prompts/test_estimation_v1.py` — 5 tests del template sin llamar al LLM

**Lo que aprendimos:**
- Un prompt en un `.j2` versionado es más mantenible que un f-string en el endpoint
- Los condicionales Jinja2 (`{% if %}`) permiten adaptar el prompt según parámetros sin duplicar código
- Los tests del template corren en milisegundos — verifican estructura, no calidad del LLM
- Formulario tipado > chat libre: el espacio de inputs queda acotado y predecible

**Decisiones arquitectónicas:**
- Versionado `v1/`, `v2/` desde el principio — cambiar el prompt no rompe clientes existentes
- `StrictUndefined` en Jinja2 — falla en desarrollo si hay un typo en el template

---

### ✅ Sesión 05 — Memoria conversacional + Adjuntos
**Qué construimos:** Sistema multi-turno con memoria del proyecto y soporte de adjuntos PDF/DOCX.

**Archivos clave:**
- `app/sessions.py` — `Session`, `ProjectMetadata`, `ConversationHistory` con ventana deslizante
- `app/services/attachment_service.py` — Extracción de texto de PDF y DOCX (Camino B)
- `app/services/llm_service.py` — Nueva función `call_llm_conversational()`
- `app/routers/estimations.py` — Nuevos endpoints de sesión
- `tests/test_sessions.py` — 3 tests de la lógica de sesión

**Nuevos endpoints:**
POST /api/v1/sessions → crea sesión, devuelve session_id
POST /api/v1/sessions/{id}/estimate → estimación conversacional con adjuntos
GET /api/v1/sessions/{id} → estado actual de la sesión

**Lo que aprendimos:**
- **Historial ≠ Memoria**: el historial es el array de mensajes (se trunca); la memoria son hechos destilados (persiste siempre)
- **Ventana deslizante** (MAX_TURNS=6): descarta turnos antiguos pero los hechos clave sobreviven en `ProjectMetadata`
- **Adjuntos Camino B**: extraer texto localmente con `pypdf`/`python-docx` es independiente del proveedor y prepara el terreno para RAG
- **Heurística** para extraer metadata: regex + vocabulario conocido, coste cero, suficiente para esta fase

**Decisiones arquitectónicas:**
- Sesiones en memoria del proceso (sin Redis ni BBDD) — aceptamos volatilidad en esta fase
- Camino B para adjuntos (extracción local) sobre Camino A (multimodal directo) — independencia de proveedor y preparación para RAG

---

### ✅ Sesión 06 — Stress test del CAG
**Qué construimos:** Medición cuantitativa de dónde rompe el CAG.

**Archivos clave:**
- `streamlit_app.py` — Conversión EUR/USD/MXN en tiempo real (frankfurter.app, caché 1h, fallback fijo)
- `app/services/llm_service.py` — Evento `turn_observed` (13 campos por turno)
- `evals/stress/` — Escenarios (growing, pivot, contradiction), PDFs sintéticos, métricas (latencia, coste, memory drift), runner y `REPORT.md`

**Hallazgos:** P50 8,658ms (SLA 4,000ms ❌) · coste ~$0.0004-0.001/turno ✅ · memory drift 62.5% ⚠️ (degrada en turno 6) → justifica RAG.

---

### 🚧 Sesión 07 — Embeddings + chunking estructural (pre-ejercicio)
**Qué construimos:** Pipeline mínimo presupuestos JSON → chunks → vectores (`text-embedding-3-small`, 1536d). Los vectores se devuelven por HTTP; la persistencia (pgvector) llega en la Sesión 08.

**Archivos clave:**
- `app/embedding_pipeline/schemas.py` — `Budget`, `BudgetComponent`, `Chunk`, `EmbeddedChunk`, `IngestRequest/Response`
- `app/embedding_pipeline/chunker.py` — `JSONStructuralChunker`: 1 componente = 1 chunk, con header contextual del presupuesto padre y metadata filtrable
- `app/embedding_pipeline/embedder.py` — `OpenAIEmbedder`: batches de 100, reintento exponencial (1s, 2s, 4s) ante `RateLimitError`, log por batch y coste estimado
- `app/embedding_pipeline/router.py` — `POST /embeddings/ingest`
- `scripts/compare.py` — Similitud coseno entre dos textos (solo biblioteca estándar)
- `app/embedding_pipeline/SANITY_CHECK.md` — Resultado de las 3 parejas de validación
- `data/budgets_sample.json` — 15 presupuestos (finance, ecommerce, healthcare, industrial), 56 componentes
- `data/ingest_request_sample.json` — Los mismos presupuestos envueltos en `{"budgets": [...]}` listos para el endpoint

**Cómo usarlo:**
```powershell
uv sync                                   # instala tiktoken
uv run uvicorn app.main:app --reload

# Ingesta (o desde Swagger: http://localhost:8000/docs → POST /embeddings/ingest)
curl.exe -X POST http://localhost:8000/embeddings/ingest `
  -H "Content-Type: application/json" `
  --data "@data/ingest_request_sample.json"

# Comparar dos textos (fuera de contenedor, con .env en la raíz)
uv run python scripts/compare.py --text-a "OAuth 2.0 authentication backend for fintech" --text-b "JWT-based authorization service for banking app"

# Ejecutar las 3 parejas oficiales y generar SANITY_CHECK.md
uv run python scripts/compare.py --sanity-check

# Dentro de contenedor (si se dockeriza el servicio en el futuro)
docker compose exec servicio_ia python scripts/compare.py --text-a "..." --text-b "..."
```

**Decisiones:**
- Contexto del padre en el texto embebido (*contextual chunk headers*); sector/año/horas también en `metadata` para filtros SQL en S08
- Sin overlap ni fixed-size: los chunks > 512 tokens solo se avisan en logs (`large_chunk_detected`)
- Sin numpy: coseno a mano; el precio del modelo es una constante etiquetada en `embedder.py`
- El proyecto no dockeriza el servicio IA (Docker solo corre Redis), así que la ejecución de referencia es con `uv`

---

## Estructura del proyecto

estimador-cag/
├── app/
│ ├── context/
│ │ └── examples.py # Ejemplos CAG (few-shot)
│ ├── prompts/
│ │ ├── loader.py # Renderizador de templates
│ │ └── estimation/v1/ # Templates Jinja2 versionados
│ ├── routers/
│ │ └── estimations.py # Endpoints FastAPI
│ ├── schemas/
│ │ └── estimation.py # Schemas Pydantic + Enums
│ ├── services/
│ │ ├── llm_service.py # Llamadas al LLM
│ │ ├── cache_service.py # Caché Redis
│ │ └── attachment_service.py # Extracción de adjuntos
│ ├── embedding_pipeline/ # S07: chunker, embedder, router, schemas
│ ├── config.py # Variables de entorno
│ ├── main.py # FastAPI app
│ └── sessions.py # Gestión de sesiones
├── tests/
│ ├── prompts/
│ │ └── test_estimation_v1.py
│ └── test_sessions.py
├── data/ # budgets_sample.json (S07)
├── evals/stress/ # Stress test del CAG (S06)
├── scripts/
│ └── compare.py # Similitud coseno (S07)
├── streamlit_app.py # Interfaz web
├── main.py # Arranque uvicorn
└── .env # API keys (no en git)