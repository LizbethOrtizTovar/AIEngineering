# evals/stress/metrics.py
"""
Tres métricas para el stress test del CAG.
Patrón MetricResult compatible con el framework existente.
Determinismo total — sin embeddings ni LLM-as-judge.
"""
from dataclasses import dataclass


@dataclass
class MetricResult:
    name:    str
    score:   float   # 0.0 o 1.0
    passed:  bool
    details: str


class LatencyBudgetMetric:
    """1.0 si latency_ms <= budget_ms; 0.0 si no."""

    def __init__(self, budget_ms: int = 4000):
        self.budget_ms = budget_ms

    def evaluate(self, latency_ms: float) -> MetricResult:
        passed = latency_ms <= self.budget_ms
        return MetricResult(
            name="LatencyBudgetMetric",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"latency={latency_ms:.0f}ms budget={self.budget_ms}ms",
        )


class CostBudgetMetric:
    """1.0 si cost_usd <= budget_usd; 0.0 si no."""

    def __init__(self, budget_usd: float = 0.01):
        self.budget_usd = budget_usd

    def evaluate(self, cost_usd: float) -> MetricResult:
        passed = cost_usd <= self.budget_usd
        return MetricResult(
            name="CostBudgetMetric",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"cost=${cost_usd:.6f} budget=${self.budget_usd:.6f}",
        )


class MemoryDriftMetric:
    """
    1.0 si el fact declarado en el turno K aparece en el snapshot
    del turno N (project_metadata o en el texto de la estimación).
    0.0 si no aparece.
    Match case-insensitive — determinismo total.
    """

    def __init__(self, fact: str):
        self.fact = fact.lower().strip()

    def evaluate(self, snapshot: dict) -> MetricResult:
        """
        snapshot debe tener:
          - project_metadata: dict con campos del proyecto
          - estimation: str con el texto de la última estimación
        """
        # Buscar en project_metadata
        metadata = snapshot.get("project_metadata", {})
        metadata_str = str(metadata).lower()

        # Buscar en el texto de estimación
        estimation = snapshot.get("estimation", "").lower()

        found_in_metadata = self.fact in metadata_str
        found_in_estimation = self.fact in estimation
        passed = found_in_metadata or found_in_estimation

        where = []
        if found_in_metadata:
            where.append("metadata")
        if found_in_estimation:
            where.append("estimation")

        return MetricResult(
            name="MemoryDriftMetric",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"fact='{self.fact}' found_in={where or 'nowhere'}",
        )