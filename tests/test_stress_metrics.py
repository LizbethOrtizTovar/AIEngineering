# tests/test_stress_metrics.py
"""
Tests unitarios para las métricas del stress test.
Corren en milisegundos — sin llamadas al LLM ni APIs externas.
"""
from evals.stress.metrics import (
    LatencyBudgetMetric,
    CostBudgetMetric,
    MemoryDriftMetric,
)


# ── LatencyBudgetMetric ───────────────────────────────────────────────────────
def test_latency_budget_passes():
    metric = LatencyBudgetMetric(budget_ms=4000)
    result = metric.evaluate(latency_ms=3500)
    assert result.passed is True
    assert result.score == 1.0


def test_latency_budget_fails():
    metric = LatencyBudgetMetric(budget_ms=4000)
    result = metric.evaluate(latency_ms=5000)
    assert result.passed is False
    assert result.score == 0.0


def test_latency_budget_exact_limit():
    metric = LatencyBudgetMetric(budget_ms=4000)
    result = metric.evaluate(latency_ms=4000)
    assert result.passed is True


# ── CostBudgetMetric ──────────────────────────────────────────────────────────
def test_cost_budget_passes():
    metric = CostBudgetMetric(budget_usd=0.01)
    result = metric.evaluate(cost_usd=0.005)
    assert result.passed is True
    assert result.score == 1.0


def test_cost_budget_fails():
    metric = CostBudgetMetric(budget_usd=0.01)
    result = metric.evaluate(cost_usd=0.05)
    assert result.passed is False
    assert result.score == 0.0


def test_cost_budget_exact_limit():
    metric = CostBudgetMetric(budget_usd=0.01)
    result = metric.evaluate(cost_usd=0.01)
    assert result.passed is True


# ── MemoryDriftMetric ─────────────────────────────────────────────────────────
def test_memory_drift_found_in_metadata():
    metric = MemoryDriftMetric(fact="NimbusPay")
    snapshot = {
        "project_metadata": {"project_name": "NimbusPay", "assumed_team_size": 3},
        "estimation": "Estimacion del proyecto de pagos.",
    }
    result = metric.evaluate(snapshot)
    assert result.passed is True
    assert "metadata" in result.details


def test_memory_drift_found_in_estimation():
    metric = MemoryDriftMetric(fact="React Native")
    snapshot = {
        "project_metadata": {"project_name": "FlutterShop"},
        "estimation": "El proyecto usa React Native para desarrollo movil.",
    }
    result = metric.evaluate(snapshot)
    assert result.passed is True
    assert "estimation" in result.details


def test_memory_drift_not_found():
    metric = MemoryDriftMetric(fact="NimbusPay")
    snapshot = {
        "project_metadata": {"project_name": "OtroProyecto"},
        "estimation": "Estimacion generica sin nombre especifico.",
    }
    result = metric.evaluate(snapshot)
    assert result.passed is False
    assert result.score == 0.0


def test_memory_drift_case_insensitive():
    metric = MemoryDriftMetric(fact="nimbuspay")
    snapshot = {
        "project_metadata": {"project_name": "NIMBUSPAY"},
        "estimation": "",
    }
    result = metric.evaluate(snapshot)
    assert result.passed is True