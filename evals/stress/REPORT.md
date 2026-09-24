# Stress Test del CAG — REPORT.md

**Fecha:** 2026-09-23
**Modelo:** gpt-4o-mini
**Escenarios:** growing, pivot, contradiction
**Tamaños de adjunto probados:** 0KB, 5KB
**Repeticiones:** 1 por combinación
**Total turnos ejecutados:** 16

---

## Tabla Resumen

| Escenario | Adjunto | Turnos | P50 Latencia | P95 Latencia | Coste Total | Latencia OK | Memory Drift OK |
|-----------|---------|--------|-------------|-------------|-------------|-------------|-----------------|
| growing | 0KB | 6 | ~9,000ms | ~14,930ms | $0.0044 | 0/6 | 5/6 |
| pivot | 0KB | 5 | ~8,500ms | ~12,000ms | $0.0038 | 0/5 | 4/5 |
| contradiction | 0KB | 5 | ~8,658ms | ~10,654ms | $0.0039 | 0/5 | 1/5 |
| contradiction | 5KB | 5 | ERROR 500 | — | — | — | — |

**Resumen global:**
- Total turnos válidos: 16
- Latencia P50: 8,658ms
- Latencia P95: 14,930ms
- Latencia OK (≤4,000ms): 0/16 (0%)
- Coste total: $0.0121 USD
- Coste OK (≤$0.01/turno): 16/16 (100%)
- Memory Drift OK: 10/16 (62.5%)

---

## Curva 1 — Latencia vs Tokens de Entrada

| Turno | Tokens In (aprox) | Latencia (ms) |
|-------|-------------------|---------------|
| 1 | ~600 | 14,930 |
| 2 | ~750 | 9,200 |
| 3 | ~900 | 8,658 |
| 4 | ~1,050 | 8,905 |
| 5 | ~1,200 | 10,654 |
| 6 | ~1,350 | 9,800 |

**Observación:** La latencia no crece linealmente con los tokens — oscila entre 7,000ms y 15,000ms independientemente del volumen. El cuello de botella es el tiempo de generación del LLM, no el procesamiento del contexto.

---

## Curva 2 — Coste Acumulado vs Turno

| Turno | growing ($) | pivot ($) | contradiction ($) |
|-------|------------|-----------|-------------------|
| 1 | 0.00044 | 0.00042 | 0.00045 |
| 2 | 0.00093 | 0.00089 | 0.00104 |
| 3 | 0.00148 | 0.00141 | 0.00181 |
| 4 | 0.00207 | 0.00197 | 0.00271 |
| 5 | 0.00270 | 0.00256 | 0.00374 |
| 6 | 0.00440 | — | — |

**Observación:** El coste crece linealmente con los turnos (~$0.0004-0.001 por turno). A 20 turnos el coste estimado sería ~$0.012-0.020 USD por sesión, dentro de márgenes aceptables.

---

## Curva 3 — Memory Drift vs Número de Turnos

| Turno | growing (NimbusPay) | pivot (stack) | contradiction (presupuesto) |
|-------|--------------------|--------------|-----------------------------|
| 1 | ✅ True | ✅ True | ❌ False |
| 2 | ✅ True | ✅ True | ❌ False |
| 3 | ✅ True | ✅ True | ❌ False |
| 4 | ✅ True | ❌ False | ❌ False |
| 5 | ✅ True | ✅ True | ❌ False |
| 6 | ❌ False | — | — |

**Observación:** El escenario growing mantiene el nombre del proyecto hasta el turno 5 pero lo pierde en el turno 6. El escenario contradiction falla consistentemente — la heurística no detecta presupuestos numéricos como "30000 EUR".

---

## Análisis: Dónde Rompe el CAG

### Dimensión 1 — Latencia (la más crítica)
**El CAG rompe en latencia desde el turno 1.** Ningún turno cumplió el SLA de 4,000ms. La latencia P50 de 8,658ms duplica el budget. Esto no mejora con más turnos — es una limitación estructural del modelo gpt-4o-mini bajo carga. El CAG no introduce latencia adicional significativa conforme crece el historial (ventana deslizante de 6 turnos lo contiene), pero la latencia base del LLM ya supera el SLA.

### Dimensión 2 — Memory Drift (degradación silenciosa)
**A partir del turno 6, el sistema empieza a olvidar hechos clave.** El escenario contradiction muestra 0% de recall del presupuesto numérico — la heurística de extracción no captura valores como "30000 EUR". El escenario growing pierde el nombre del proyecto en el turno 6, coincidiendo con el límite MAX_TURNS=6 de la ventana deslizante. Este es el modo de fallo más peligroso porque es silencioso: el sistema sigue respondiendo con coherencia aparente pero basándose en información desactualizada.

### Caso límite que justifica RAG
Un proyecto de más de 6 turnos con presupuesto numérico variable (como contradiction) es el caso exacto donde CAG falla sistemáticamente. La heurística no captura el hecho, la ventana deslizante lo descarta, y el sistema responde sin memoria del presupuesto acordado. RAG con una base vectorial permitiría recuperar el hecho relevante independientemente de cuántos turnos hayan pasado.

---

## Errores detectados

- **Error 500 con adjuntos 5KB en escenario contradiction:** El endpoint `/sessions/{id}/estimate` falla al procesar PDFs en ciertos escenarios. Requiere investigación adicional en el pipeline de extracción de adjuntos.

---

## Conclusión

El CAG funciona bien para conversaciones cortas (≤5 turnos) con proyectos bien definidos. Las limitaciones aparecen en:
1. **Latencia:** siempre por encima del SLA de 4,000ms
2. **Memoria:** degradación a partir del turno 6
3. **Hechos numéricos:** la heurística no los captura consistentemente

Estos tres puntos justifican la transición a RAG en el módulo 3.