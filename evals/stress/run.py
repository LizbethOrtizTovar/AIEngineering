# evals/stress/run.py
"""
Runner del stress test del CAG.
Ejecutar: uv run python -m evals.stress.run --http http://localhost:8000
"""
import argparse
import csv
import time
from pathlib import Path
from datetime import datetime
import requests

from evals.stress.scenarios import ALL_SCENARIOS
from evals.stress.metrics import LatencyBudgetMetric, CostBudgetMetric, MemoryDriftMetric

OUTPUT_DIR = Path(__file__).parent
FIXTURES_DIR = OUTPUT_DIR / "fixtures"

ATTACHMENT_SIZES = [0, 5, 20, 50, 100]

latency_metric = LatencyBudgetMetric(budget_ms=4000)
cost_metric    = CostBudgetMetric(budget_usd=0.01)


def get_pdf_path(size_kb: int) -> Path | None:
    if size_kb == 0:
        return None
    path = FIXTURES_DIR / f"attach_{size_kb}kb.pdf"
    return path if path.exists() else None


def run_scenario(base_url: str, scenario, attachment_kb: int, repeat: int) -> list[dict]:
    """Ejecuta un escenario completo y devuelve filas para el CSV."""
    rows = []

    # Crear sesión
    resp = requests.post(f"{base_url}/api/v1/sessions")
    session_id = resp.json()["session_id"]

    pdf_path = get_pdf_path(attachment_kb)

    for turn in scenario.turns:
        start = time.time()

        # Preparar request
        data = {
            "transcription": turn.transcript,
            "project_type":  "web_saas",
            "detail_level":  "medium",
            "output_format": "phases_table",
        }

        files = None
        if pdf_path:
            files = [("attachments", (pdf_path.name, pdf_path.read_bytes(), "application/pdf"))]

        # Llamar al endpoint
        try:
            resp = requests.post(
                f"{base_url}/api/v1/sessions/{session_id}/estimate",
                data=data,
                files=files,
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            print(f"  ERROR turno {turn.turn_index}: {e}")
            continue

        latency_ms = round((time.time() - start) * 1000, 2)

        # Obtener estado de la sesión
        state_resp = requests.get(f"{base_url}/api/v1/sessions/{session_id}")
        session_state = state_resp.json() if state_resp.status_code == 200 else {}

        # Calcular coste
        usage = result.get("usage", {})
        tokens_in  = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        cost_usd   = round((tokens_in * 0.00000015) + (tokens_out * 0.0000006), 6)

        # Evaluar métricas
        lat_result  = latency_metric.evaluate(latency_ms)
        cost_result = cost_metric.evaluate(cost_usd)

        # MemoryDriftMetric si hay fact_to_remember
        memory_passed = None
        if turn.fact_to_remember:
            mem_metric = MemoryDriftMetric(fact=turn.fact_to_remember)
            snapshot = {
                "project_metadata": session_state.get("project_metadata", {}),
                "estimation":       result.get("estimation", ""),
            }
            mem_result    = mem_metric.evaluate(snapshot)
            memory_passed = mem_result.passed

        row = {
            "timestamp":         datetime.utcnow().isoformat(),
            "scenario":          scenario.name,
            "attachment_kb":     attachment_kb,
            "repeat":            repeat,
            "turn_index":        turn.turn_index,
            "session_id":        session_id,
            "tokens_in":         tokens_in,
            "tokens_out":        tokens_out,
            "cost_usd":          cost_usd,
            "latency_ms":        latency_ms,
            "latency_ok":        lat_result.passed,
            "cost_ok":           cost_result.passed,
            "memory_drift_ok":   memory_passed,
            "fact_to_remember":  turn.fact_to_remember or "",
            "model":             result.get("model", ""),
            "cache_hit":         result.get("cache_hit", False),
        }
        rows.append(row)

        status = "✅" if lat_result.passed else "⚠️"
        print(f"  {status} Turno {turn.turn_index} | {latency_ms:.0f}ms | ${cost_usd:.5f} | memory={memory_passed}")

    return rows


def main():
    parser = argparse.ArgumentParser(description="Stress test del CAG")
    parser.add_argument("--http",     default="http://localhost:8000")
    parser.add_argument("--repeats",  type=int, default=2)
    parser.add_argument("--output",   default=str(OUTPUT_DIR / "results.csv"))
    parser.add_argument("--sizes",    default="0,5,20", help="Tamaños de adjuntos en KB separados por coma")
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    all_rows = []

    print(f"\n🚀 Stress test CAG — {len(ALL_SCENARIOS)} escenarios × {len(sizes)} tamaños × {args.repeats} repeticiones\n")

    for scenario in ALL_SCENARIOS:
        for size_kb in sizes:
            for repeat in range(1, args.repeats + 1):
                print(f"\n📋 Escenario: {scenario.name} | Adjunto: {size_kb}KB | Repetición: {repeat}/{args.repeats}")
                rows = run_scenario(args.http, scenario, size_kb, repeat)
                all_rows.extend(rows)

    # Escribir CSV
    if all_rows:
        output_path = Path(args.output)
        fieldnames = list(all_rows[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\n✅ CSV guardado: {output_path} ({len(all_rows)} filas)")

    # Resumen
    if all_rows:
        latencies = [r["latency_ms"] for r in all_rows]
        costs     = [r["cost_usd"] for r in all_rows]
        lat_ok    = sum(1 for r in all_rows if r["latency_ok"])
        cost_ok   = sum(1 for r in all_rows if r["cost_ok"])
        mem_rows  = [r for r in all_rows if r["memory_drift_ok"] is not None]
        mem_ok    = sum(1 for r in mem_rows if r["memory_drift_ok"])

        print(f"\n📊 RESUMEN")
        print(f"  Total turnos:        {len(all_rows)}")
        print(f"  Latencia P50:        {sorted(latencies)[len(latencies)//2]:.0f}ms")
        print(f"  Latencia P95:        {sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms")
        print(f"  Latencia OK:         {lat_ok}/{len(all_rows)}")
        print(f"  Coste total:         ${sum(costs):.4f} USD")
        print(f"  Coste OK:            {cost_ok}/{len(all_rows)}")
        if mem_rows:
            print(f"  Memory drift OK:     {mem_ok}/{len(mem_rows)}")


if __name__ == "__main__":
    main()