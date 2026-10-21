"""Variantes de Hill Climbing con telemetría paso a paso.

La lógica del algoritmo vive aquí y se expone como *generadores*: cada
``yield`` entrega un :class:`StepInfo` con TODA la información de una
iteración (estado, ``f`` actual, vecinos evaluados con su ``Δf`` y la razón de
la decisión). La CLI y la GUI solo consumen ``next()``, de modo que el modo
paso a paso no duplica código.

Variantes disponibles (``VARIANTS``):

* ``simple``        - primer vecino que mejora en el orden fijo ↑ ↓ ← →.
* ``steepest``      - vecino con mayor ``Δf`` (empate: primero en orden fijo,
  o aleatorio con ``desempate="aleatorio"``).
* ``stochastic``    - elección probabilística proporcional a ``Δf`` (con semilla).
* ``first_choice``  - primer vecino *aleatorio* que mejora (orden barajado).

Mitigaciones combinables: movimientos laterales con límite
(``sideways_limit``), penalización por estancamiento ``f'(s) = f(s) - λ·n(s)``
(``penalty_lambda``) y reinicios aleatorios (:func:`random_restart`).

Para medir el coste de la telemetría existe :func:`hill_climbing_ligero`, que
resuelve el mismo problema **sin** construir objetos ``StepInfo``.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator, Protocol, Sequence

from .maze import Cell, Maze


class VecinoEvaluado(Protocol):
    """Lo mínimo que necesita :func:`_select` de un vecino evaluado."""

    cell: Cell
    delta: float
    arrow: str

#: Tipo de desempate permitido para la variante *steepest*.
DESEMPATES = ("fijo", "aleatorio")


@dataclass
class Evaluation:
    """Un vecino de ``N(s)`` evaluado durante la iteración."""

    arrow: str
    cell: Cell
    f: float  # f'(vecino)
    delta: float  # f'(vecino) - f'(actual)
    inspected: bool = True  # False si first_choice no llegó a evaluarlo


@dataclass
class StepInfo:
    """Telemetría completa de UNA iteración."""

    iteration: int
    current: Cell
    f_current: float
    evaluations: list[Evaluation]
    chosen: Cell | None
    decision: str  # razón de la decisión, en español
    status: str = "running"  # running | goal | local_max | plateau | max_iter
    moves: int = 0
    restart: int = 0
    penalties: dict[Cell, int] = field(default_factory=dict)
    stalls: int = 0  # veces que la ejecución se ha estancado (sin mitigación efectiva)


VARIANTS = ("simple", "steepest", "stochastic", "first_choice")

#: Etiquetas en español del resultado final de una ejecución.
ETIQUETAS = {
    "goal": "META ALCANZADA",
    "local_max": "ATRAPADO EN MÁXIMO LOCAL",
    "plateau": "ATRAPADO EN MESETA",
    "max_iter": "LÍMITE DE ITERACIONES ALCANZADO",
    "max_reinicios": "REINICIOS AGOTADOS",
}

#: Estados que cuentan como estancamiento (no llegó a la meta).
ESTANCAMIENTOS = ("local_max", "plateau", "max_iter", "max_reinicios")


def _select(
    variant: str,
    evals: Sequence[VecinoEvaluado],
    rng: random.Random,
    desempate: str = "fijo",
):
    """Regla de avance. Devuelve ``(Evaluation elegida, razón)`` o ``(None, razón)``."""
    better = [e for e in evals if e.delta > 0]
    if not better:
        return None, "Ningún vecino mejora: todos los Δf ≤ 0."
    if variant == "steepest":
        # Empate: el primero en el orden de exploración (desempate estable),
        # o uno al azar entre los empatados si se pide desempate aleatorio.
        mejor_delta = max(e.delta for e in better)
        empatados = [e for e in better if e.delta == mejor_delta]
        if desempate == "aleatorio" and len(empatados) > 1:
            e = rng.choice(empatados)
            return e, (
                f"Ascenso más pronunciado: {e.arrow} {e.cell} con Δf = {e.delta:+.2f} "
                f"(elegido al azar entre {len(empatados)} empatados)."
            )
        e = empatados[0]
        return e, f"Ascenso más pronunciado: {e.arrow} {e.cell} con Δf = {e.delta:+.2f}."
    if variant == "simple":
        e = better[0]  # primero que mejora en el orden fijo
        return e, f"Primer vecino que mejora en orden fijo: {e.arrow} {e.cell}, Δf = {e.delta:+.2f}."
    if variant == "stochastic":
        e = rng.choices(better, weights=[x.delta for x in better])[0]
        return e, (
            f"Elección probabilística ∝ Δf entre {len(better)} vecino(s) ascendente(s): "
            f"{e.arrow} {e.cell}."
        )
    if variant == "first_choice":
        e = better[0]  # evals ya viene barajado
        return e, f"Primer vecino aleatorio que mejora: {e.arrow} {e.cell}, Δf = {e.delta:+.2f}."
    raise ValueError(variant)


def hill_climbing(
    maze: Maze,
    start: Cell,
    variant: str = "steepest",
    metric: str = "manhattan",
    rng: random.Random | None = None,
    sideways_limit: int = 0,
    penalty_lambda: float = 0.0,
    max_iter: int = 5000,
    vecindad: int = 4,
    orden: tuple[tuple[str, int, int], ...] | None = None,
    desempate: str = "fijo",
) -> Iterator[StepInfo]:
    """Generador: cada ``yield`` es UNA iteración con su telemetría (modo paso a paso).

    Termina (``return``) al alcanzar la meta, al detectar máximo local / meseta
    o al agotar ``max_iter``.

    ``vecindad`` acepta 4 u 8 direcciones; ``orden`` permite pasar una
    permutación concreta de las direcciones (por defecto el orden canónico).
    """
    if variant not in VARIANTS:
        raise ValueError(f"Variante desconocida: {variant!r}")
    if desempate not in DESEMPATES:
        raise ValueError(f"Desempate desconocido: {desempate!r}")
    rng = rng or random.Random()
    cur: Cell = start
    moves, sideways, stalls = 0, 0, 0
    prev: Cell | None = None  # celda anterior (evita rebotes en movimientos laterales)
    # n(s) = veces que el algoritmo se ha estancado en s (penalización acumulada)
    n: dict[Cell, int] = defaultdict(int)

    def fp(s: Cell) -> float:
        return maze.f(s, metric) - penalty_lambda * n[s]

    for it in range(1, max_iter + 1):
        f_cur = fp(cur)

        # --- condición de terminación por meta ---------------------------------
        if cur == maze.goal:
            yield StepInfo(
                it, cur, f_cur, [], None,
                "Meta alcanzada: f = 0 (óptimo global).", "goal", moves,
                penalties=dict(n), stalls=stalls,
            )
            return

        neigh = maze.neighbors(cur, vecindad=vecindad, orden=orden)
        if not neigh:
            yield StepInfo(
                it, cur, f_cur, [], None,
                "Celda aislada: no existe ningún vecino libre que evaluar.",
                "local_max", moves, penalties=dict(n), stalls=stalls,
            )
            return

        if variant == "first_choice":
            rng.shuffle(neigh)
        evals = [Evaluation(a, s, fp(s), fp(s) - f_cur) for a, s in neigh]
        chosen, why = _select(variant, evals, rng, desempate)

        # --- movimiento ascendente (Δf > 0) -----------------------------------
        if chosen:
            moves += 1
            sideways = 0
            yield StepInfo(
                it, cur, f_cur, evals, chosen.cell, why, "running", moves,
                penalties=dict(n), stalls=stalls,
            )
            prev, cur = cur, chosen.cell
            continue

        # --- movimiento lateral con límite (Δf = 0) ---------------------------
        lateral = [e for e in evals if e.delta == 0]
        if lateral and sideways < sideways_limit:
            # Evita ciclos: si hay alternativa, no se vuelve a la celda previa.
            candidatos = [e for e in lateral if e.cell != prev] or lateral
            e = candidatos[0]
            sideways += 1
            moves += 1
            yield StepInfo(
                it, cur, f_cur, evals, e.cell,
                f"Movimiento lateral {sideways}/{sideways_limit} (Δf = 0): {e.arrow} {e.cell}.",
                "running", moves, penalties=dict(n), stalls=stalls,
            )
            prev, cur = cur, e.cell
            continue

        # --- mitigación por penalización --------------------------------------
        if penalty_lambda > 0:
            stalls += 1
            n[cur] += 1
            yield StepInfo(
                it, cur, f_cur, evals, None,
                f"Estancado en {cur}: se penaliza n={n[cur]} -> f' = {fp(cur):.2f}. Se reintenta.",
                "running", moves, penalties=dict(n), stalls=stalls,
            )
            continue

        # --- terminación: máximo local o meseta --------------------------------
        stalls += 1
        if lateral:
            why = "Meseta: hay vecinos con Δf = 0 y ninguno con Δf > 0."
            status = "plateau"
        else:
            why = (
                "Máximo local: todos los vecinos tienen Δf < 0 y "
                f"f = {f_cur:.2f} < 0 (óptimo global)."
            )
            status = "local_max"
        yield StepInfo(
            it, cur, f_cur, evals, None, why, status, moves,
            penalties=dict(n), stalls=stalls,
        )
        return

    yield StepInfo(
        max_iter, cur, fp(cur), [], None, "Límite de iteraciones alcanzado.",
        "max_iter", moves, penalties=dict(n), stalls=stalls,
    )


def hill_climbing_ligero(
    maze: Maze,
    start: Cell,
    variant: str = "steepest",
    metric: str = "manhattan",
    rng: random.Random | None = None,
    sideways_limit: int = 0,
    penalty_lambda: float = 0.0,
    max_iter: int = 5000,
    vecindad: int = 4,
    orden: tuple[tuple[str, int, int], ...] | None = None,
    desempate: str = "fijo",
) -> dict:
    """Misma lógica que :func:`hill_climbing` pero SIN telemetría.

    Devuelve ``{"status", "iteraciones", "movimientos"}``. Existe solo para
    medir cuánto cuesta construir la telemetría; no debe usarse en la GUI.
    """
    if variant not in VARIANTS:
        raise ValueError(f"Variante desconocida: {variant!r}")
    if desempate not in DESEMPATES:
        raise ValueError(f"Desempate desconocido: {desempate!r}")
    rng = rng or random.Random()
    cur: Cell = start
    moves, sideways = 0, 0
    prev: Cell | None = None
    n: dict[Cell, int] = defaultdict(int)

    def fp(s: Cell) -> float:
        return maze.f(s, metric) - penalty_lambda * n[s]

    for it in range(1, max_iter + 1):
        if cur == maze.goal:
            return {"status": "goal", "iteraciones": it, "movimientos": moves}
        f_cur = fp(cur)
        neigh = maze.neighbors(cur, vecindad=vecindad, orden=orden)
        if not neigh:
            return {"status": "local_max", "iteraciones": it, "movimientos": moves}
        if variant == "first_choice":
            rng.shuffle(neigh)
        evals = [
            _EvalLigero(s, fp(s) - f_cur)
            for _, s in neigh
        ]
        chosen, _ = _select(variant, evals, rng, desempate)
        if chosen is not None:
            moves += 1
            sideways = 0
            prev, cur = cur, chosen.cell
            continue
        lateral = any(e.delta == 0 for e in evals)
        if lateral and sideways < sideways_limit:
            cand = [e for e in evals if e.delta == 0 and e.cell != prev]
            e = (cand or [e for e in evals if e.delta == 0])[0]
            sideways += 1
            moves += 1
            prev, cur = cur, e.cell
            continue
        if penalty_lambda > 0:
            n[cur] += 1
            continue
        return {
            "status": "plateau" if lateral else "local_max",
            "iteraciones": it,
            "movimientos": moves,
        }
    return {"status": "max_iter", "iteraciones": max_iter, "movimientos": moves}


class _EvalLigero:
    """Vecino mínimo para el modo sin telemetría (compatible con ``_select``)."""

    __slots__ = ("cell", "delta", "arrow")

    def __init__(self, cell: Cell, delta: float) -> None:
        self.cell = cell
        self.delta = delta
        self.arrow = ""


def ejecutar(maze: Maze, start: Cell, **kw) -> StepInfo:
    """Ejecuta una variante hasta el final y devuelve la telemetría de la última iteración."""
    info: StepInfo | None = None
    for info in hill_climbing(maze, start, **kw):
        pass
    if info is None:  # pragma: no cover - el generador siempre emite al menos un paso
        raise RuntimeError("El generador no produjo ninguna iteración")
    return info


def random_restart(
    maze: Maze,
    start: Cell,
    rng: random.Random,
    max_restarts: int = 100,
    **kw,
) -> Iterator[StepInfo]:
    """Reinicios aleatorios.

    El primer intento parte de ``start``; los siguientes de una celda libre
    uniforme. Devuelve en cuanto una ejecución alcanza la meta; si se agotan
    ``max_restarts`` sin éxito, emite un paso final con estado
    ``max_reinicios``.
    """
    libres = maze.free_cells()
    mv_total, intentos = 0, 0
    for r in range(max_restarts + 1):
        s = start if r == 0 else rng.choice(libres)
        intentos += 1
        for info in hill_climbing(maze, s, rng=rng, **kw):
            info.restart = r
            yield info
            if info.chosen is not None:
                mv_total += 1
        ultimo = info
        if ultimo.status == "goal":
            return
    # Ningún intento alcanzó la meta: se agotó el presupuesto de reinicios.
    yield StepInfo(
        ultimo.iteration, ultimo.current, ultimo.f_current, [], None,
        f"Reinicios agotados: {intentos} intento(s) y {max_restarts} reinicio(s) "
        "sin alcanzar la meta.",
        "max_reinicios", mv_total, restart=max_restarts,
        penalties=dict(ultimo.penalties), stalls=ultimo.stalls,
    )
