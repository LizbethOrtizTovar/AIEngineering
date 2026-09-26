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
### ✅ Sesión 06 — Stress test CAG + Divisas en tiempo real
**Qué construimos:** Medición cuantitativa de los límites del CAG y conversión de divisas.

**Archivos clave:**
- `streamlit_app.py` — conversión EUR/USD/MXN en tiempo real (frankfurter.app, caché 1h, fallback fijo)
- `app/services/llm_service.py` — evento `turn_observed` con 13 campos structlog
- `evals/stress/scenarios.py` — 3 escenarios: growing, pivot, contradiction
- `evals/stress/metrics.py` — LatencyBudgetMetric, CostBudgetMetric, MemoryDriftMetric (10/10 tests)
- `evals/stress/run.py` — runner que genera results.csv
- `evals/stress/REPORT.md` — análisis completo con 3 curvas

**Hallazgos del stress test:**
- Latencia P50: 8,658ms — supera SLA de 4,000ms ❌
- Coste por turno: ~$0.0004-0.001 ✅
- Memory drift: 10/16 (62.5%) — degrada en turno 6 ⚠️
- Conclusión: justifica transición a RAG en módulo 3

**Lo que aprendimos:**
- El CAG rompe en latencia desde el turno 1 — limitación estructural del LLM
- La memoria heurística falla con hechos numéricos (presupuestos)
- La ventana deslizante de 6 turnos es el límite natural del CAG

---

### ✅ Sesión 07 — Embeddings y Chunking (pre-ejercicio)
**Qué construimos:** Pipeline de embeddings para preparar el terreno para RAG.

**Archivos clave:**
- `app/embedding_pipeline/schemas.py` — Budget, BudgetComponent, EmbeddedChunk, IngestRequest/Response
- `app/embedding_pipeline/chunker.py` — JSONStructuralChunker con headers contextuales
- `app/embedding_pipeline/embedder.py` — batch de 100, reintentos 1/2/4s, log por batch
- `app/embedding_pipeline/router.py` — POST /embeddings/ingest
- `scripts/compare.py` — sanity check con similitud coseno
- `data/budgets_sample.json` — 15 presupuestos sintéticos, 56 componentes
- `app/embedding_pipeline/SANITY_CHECK.md` — resultados documentados

**Resultados del sanity check:**
| Pareja | Coseno | Esperado |
|--------|--------|----------|
| Textos cercanos (OAuth + autenticación) | 0.5958 | >0.6 |
| Textos no relacionados | 0.1920 | <0.4 |
| Textos genéricos | 0.5408 | — |

**Lo que aprendimos:**
- Embeddings = texto → vector de 1536 números (text-embedding-3-small)
- Textos similares → vectores similares (coseno alto)
- Chunking: 1 componente de presupuesto = 1 chunk con header contextual
- El orden de similitud es correcto — separación de 0.40 entre cercanos y no relacionados
- Textos vagos inflan la similitud (riesgo con briefs poco detallados)

**Decisión técnica:** text-embedding-3-small, 1536d, $0.02/1M tokens

### ✅ Sesión 08 — Base de datos vectorial con pgvector
**Qué construimos:** Persistencia de embeddings en PostgreSQL con pgvector y búsqueda semántica.

**Archivos clave:**
- `app/db.py` — conexión SQLAlchemy + inicialización de pgvector, tabla y índices
- `app/embedding_pipeline/router.py` — actualizado para persistir chunks en PostgreSQL
- `app/embedding_pipeline/retrieval.py` — búsqueda semántica con operador `<=>` de pgvector
- `app/main.py` — inicializa la BD en startup

**Nuevos endpoints:**
POST /embeddings/ingest → chunking + embeddings + persistencia en PostgreSQL
POST /embeddings/search → búsqueda semántica top-k con filtros de metadata


**Infraestructura:**
- PostgreSQL 16 con pgvector en Docker (`pgvector/pgvector:pg16`)
- Índice HNSW (m=16, ef_construction=64) para búsqueda aproximada rápida
- Índices de metadata en sector, tecnología, año y complejidad

**Resultado del test de búsqueda:**
Query: "OAuth authentication for mobile banking app"
| Chunk | Similitud | Sector | Tech | Horas |
|-------|-----------|--------|------|-------|
| BUD-2024-014::AUTH-003 | 0.5918 | finance | fastapi | 70 |
| BUD-2023-003::AUTH-001 | 0.5564 | finance | ruby_on_rails | 120 |
| BUD-2023-003::PSD2-002 | 0.5108 | finance | ruby_on_rails | 160 |

**Lo que aprendimos:**
- pgvector añade el operador `<=>` (distancia coseno) a PostgreSQL
- Índice HNSW: búsqueda aproximada, mucho más rápida que fuerza bruta a partir de ~10k vectores
- `ON CONFLICT DO UPDATE` permite reingestión sin duplicados
- Los filtros de metadata combinados con búsqueda vectorial permiten RAG con contexto
- La similitud coseno entre 0.5 y 0.6 indica relevancia real en este corpus

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
│ ├── config.py # Variables de entorno
│ ├── main.py # FastAPI app
│ └── sessions.py # Gestión de sesiones
├── tests/
│ ├── prompts/
│ │ └── test_estimation_v1.py
│ └── test_sessions.py
├── streamlit_app.py # Interfaz web
├── main.py # Arranque uvicorn
└── .env # API keys (no en git)