# evals/stress/scenarios.py
"""
Tres escenarios sintéticos para stress test del CAG.
Cada escenario es una lista de turnos con un hecho a recordar.
"""
from dataclasses import dataclass


@dataclass
class Turn:
    turn_index: int
    transcript: str
    fact_to_remember: str | None = None  # hecho que debe persistir en turnos posteriores


@dataclass
class Scenario:
    name: str
    description: str
    turns: list[Turn]


# ── Escenario 1: Proyecto que crece ──────────────────────────────────────────
GROWING_PROJECT = Scenario(
    name="growing",
    description="Turno a turno se añaden requisitos. Mide si el nombre del proyecto sobrevive.",
    turns=[
        Turn(1, "El proyecto se llama NimbusPay. Necesitamos una pasarela de pagos online con React y Node.", "NimbusPay"),
        Turn(2, "Añadir autenticacion de dos factores para los usuarios.", "NimbusPay"),
        Turn(3, "Necesitamos soporte multi-tenant para que varios comercios usen la plataforma.", "NimbusPay"),
        Turn(4, "Agregar un modulo de audit log para registrar todas las transacciones.", "NimbusPay"),
        Turn(5, "Exportacion de reportes en CSV y PDF mensualmente.", "NimbusPay"),
        Turn(6, "Panel de administracion para gestionar comercios y ver estadisticas en tiempo real.", "NimbusPay"),
    ]
)

# ── Escenario 2: Proyecto que pivota ─────────────────────────────────────────
PIVOT_PROJECT = Scenario(
    name="pivot",
    description="El turno 3 cambia el stack. Mide si la metadata se actualiza limpiamente.",
    turns=[
        Turn(1, "Proyecto FlutterShop: app movil de ecommerce con React Native y PostgreSQL.", "React Native"),
        Turn(2, "Necesitamos carrito de compras y pasarela de pagos con Stripe.", "React Native"),
        Turn(3, "El cliente ha decidido cambiar a Flutter en lugar de React Native por mejor rendimiento.", "Flutter"),
        Turn(4, "Integrar notificaciones push con Firebase para iOS y Android.", "Flutter"),
        Turn(5, "Añadir modo offline con sincronizacion cuando recupere conexion.", "Flutter"),
    ]
)

# ── Escenario 3: Proyecto que se contradice ───────────────────────────────────
CONTRADICTION_PROJECT = Scenario(
    name="contradiction",
    description="El presupuesto cambia entre turnos. Mide cual se preserva.",
    turns=[
        Turn(1, "Proyecto DataVault: sistema de gestion documental con presupuesto de 30000 EUR.", "30000 EUR"),
        Turn(2, "El equipo sera de 2 desarrolladores senior usando Python y FastAPI.", "30000 EUR"),
        Turn(3, "Tras revision interna el presupuesto se ha ampliado a 80000 EUR por mayor alcance.", "80000 EUR"),
        Turn(4, "Añadir modulo de busqueda full-text con Elasticsearch.", "80000 EUR"),
        Turn(5, "El cliente ha confirmado el presupuesto final de 80000 EUR y firmado el contrato.", "80000 EUR"),
    ]
)

ALL_SCENARIOS = [GROWING_PROJECT, PIVOT_PROJECT, CONTRADICTION_PROJECT]