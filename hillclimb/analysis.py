"""Análisis del paisaje de búsqueda y teoría de los reinicios aleatorios.

Aqué se miden las magnitudes que el reporte necesita:

* :func:`barrier_depth` - profundidad de la barrera de un máximo local.
* :func:`basin_of_attraction` - ejecución exhaustiva desde cada celda libre,
  de la que sale la probabilidad de éxito ``p = |B(g)| / |F|``.
* :func:`expected_restarts`, :func:`success_after`, :func:`expected_cost` -
  fórmulas teóricas de los reinicios aleatorios, para compararlas con lo medido.
"""

from __future__ import annotations

import heapq
import itertools
import math
import random
import statistics
from collections import defaultdict

from .algorithms import StepInfo, ejecutar, random_restart
from .maze import MOVES, Cell, Maze


def barrier_depth(maze: Maze, cell: Cell, metric: str = "manhattan") -> float:
    """d(s°) = f(s°) - M.

    ``M`` es el máximo, sobre todos los caminos que llevan a un estado mejor,
    del mínimo de ``f`` a lo largo del camino (búsqueda del camino *maximín*).
    Equivale a la profundidad del hoyo que hay que escalar para escapar de
    ``cell``. Devuelve ``math.inf`` si no existe ningún estado alcanzable mejor.
    """
    f0 = maze.f(cell, metric)
    best: dict[Cell, float] = {cell: f0}
    pq: list[tuple[float, Cell]] = [(-f0, cell)]
    while pq:
        negm, s = heapq.heappop(pq)
        m = -negm
        if best.get(s, -math.inf) > m:
            continue
        if maze.f(s, metric) > f0:
            return f0 - m
        for _, t in maze.neighbors(s):
            m2 = min(m, maze.f(t, metric))
            if m2 > best.get(t, -math.inf):
                best[t] = m2
                heapq.heappush(pq, (-m2, t))
    return math.inf


def basin_of_attraction(
    maze: Maze,
    variant: str = "steepest",
    metric: str = "manhattan",
    **kw,
) -> dict[Cell, list[Cell]]:
    """Ejecuta la variante desde CADA celda libre y agrupa por estado final.

    Devuelve ``{estado_final: [celdas_iniciales]}``. La cuenca de la meta
    ``B(g)`` es el valor asociado a ``maze.goal``; si ``p = |B(g)|/|F|`` es 1,
    no existe ningún máximo local alcanzable.
    """
    cuencas: dict[Cell, list[Cell]] = defaultdict(list)
    for s in maze.free_cells():
        info: StepInfo = ejecutar(maze, s, variant=variant, metric=metric, **kw)
        cuencas[info.current].append(s)
    return dict(cuencas)


def basin_stats(
    maze: Maze,
    variant: str = "steepest",
    metric: str = "manhattan",
    **kw,
) -> dict:
    """Resumen numérico de las cuencas de atracción.

    Devuelve ``p`` (probabilidad de éxito desde una celda libre uniforme),
    el porcentaje de estancamiento ``1 - p``, el número de celdas libres, la
    cuenca de la meta y las celdas atrapadas por máximo local/meseta.
    """
    cuencas = basin_of_attraction(maze, variant=variant, metric=metric, **kw)
    total = len(maze.free_cells())
    exito = len(cuencas.get(maze.goal, []))  # type: ignore[arg-type]
    p = exito / total if total else 0.0
    return {
        "p": p,
        "estancamiento": 1.0 - p,
        "libres": total,
        "exito": exito,
        "cuencas": cuencas,
        "atrapadas": {
            celda: celdas
            for celda, celdas in cuencas.items()
            if celda != maze.goal
        },
    }


def expected_restarts(p: float) -> float:
    """Reinicios esperados hasta el primer éxito: ``E[r] = 1/p``."""
    if p <= 0:
        return math.inf
    return 1.0 / p


def success_after(p: float, r: int) -> float:
    """Probabilidad de éxito tras ``r`` reinicios: ``1 - (1 - p)^r``."""
    return 1.0 - (1.0 - p) ** r


def expected_cost(p: float, t_f: float, t_s: float) -> float:
    """Costo esperado de reinicios aleatorios: ``((1-p)/p)·t_f + t_s``."""
    if p <= 0:
        return math.inf
    return ((1.0 - p) / p) * t_f + t_s


def escape_iterations(maze: Maze, start: Cell, penalty_lambda: float, metric: str = "manhattan") -> tuple[str, int]:
    """Iteraciones que tarda la penalización (λ) en escapar desde ``start``.

    Devuelve ``(estado_final, iteraciones)``.
    """
    info = ejecutar(
        maze, start, variant="steepest", metric=metric,
        penalty_lambda=penalty_lambda, max_iter=5000,
    )
    return info.status, info.iteration


def mesetas_posibles(maze: Maze, metric: str = "manhattan") -> dict:
    """¿Puede existir una meseta con la vecindad de 8 direcciones?

    Comprueba, celda por celda, la implicación::

        «tener un vecino con Δf = 0»  ⇒  «tener un vecino con Δf > 0»

    Con la regla de *no cortar esquinas*, un movimiento diagonal solo se admite
    si las dos celdas cardinales adyacentes están libres; y esas dos celdas
    tienen ``Δf > 0`` respecto al estado actual. Por tanto una meseta (sin
    vecino ascendente pero con alguno lateral) es **inalcanzable**, y los
    movimientos laterales nunca se activan por sí solos.

    Devuelve el recuento de celdas en cada categoría.
    """
    con_lateral = con_ascendente = solo_lateral = 0
    for s in maze.free_cells():
        vecinos = maze.neighbors(s, vecindad=8)
        if not vecinos:
            continue
        f_s = maze.f(s, metric)
        laterales = [t for _, t in vecinos if maze.f(t, metric) == f_s]
        if not laterales:
            continue
        con_lateral += 1
        if any(maze.f(t, metric) > f_s for _, t in vecinos):
            con_ascendente += 1
        else:
            solo_lateral += 1
    return {
        "libres": len(maze.free_cells()),
        "con_lateral": con_lateral,
        "con_lateral_y_ascendente": con_ascendente,
        "solo_lateral": solo_lateral,
    }


def restart_iterations(maze: Maze, start: Cell, rng_seed: int, max_restarts: int = 100, metric: str = "manhattan") -> tuple[str, int, int]:
    """Reinicio aleatorios desde ``start``: ``(estado, reinicios_usados, iteraciones)``."""
    import random

    info: StepInfo | None = None
    for info in random_restart(maze, start, random.Random(rng_seed), max_restarts=max_restarts, metric=metric):
        pass
    if info is None:  # pragma: no cover
        raise RuntimeError("El generador no produjo ninguna iteración")
    return info.status, info.restart, info.iteration


# ------------------------------------------------------------------ desempate
def _p_de_orden(maze: Maze, orden, metric: str = "manhattan") -> float:
    """Probabilidad de éxito del steepest usando una permutación concreta de N(s)."""
    exitos = 0
    for s in maze.free_cells():
        info = ejecutar(maze, s, variant="steepest", metric=metric, orden=orden)
        if info.status == "goal":
            exitos += 1
    total = len(maze.free_cells())
    return exitos / total if total else 0.0


def sensibilidad_desempate(maze: Maze, semillas: int = 1000, metric: str = "manhattan") -> dict:
    """Cómo depende ``p`` de la regla de desempate del empate en *steepest*.

    Devuelve las ``p`` de las 24 permutaciones del orden de movimientos y de
    ``semillas`` ejecuciones con desempate aleatorio, más mínimo, máximo, media
    y desviación estándar de cada familia.
    """
    libres = len(maze.free_cells())

    permutaciones = {
        "".join(a for a, _, _ in perm): _p_de_orden(maze, perm, metric)
        for perm in itertools.permutations(MOVES)
    }
    vals_perm = list(permutaciones.values())

    aleatorias: list[float] = []
    for semilla in range(semillas):
        exitos = 0
        for s in maze.free_cells():
            info = ejecutar(
                maze, s, variant="steepest", metric=metric,
                desempate="aleatorio", rng=random.Random(semilla * 131071 + exitos),
            )
            if info.status == "goal":
                exitos += 1
        aleatorias.append(exitos / libres if libres else 0.0)

    return {
        "libres": libres,
        "orden_fijo_p": _p_de_orden(maze, MOVES, metric),
        "permutaciones": permutaciones,
        "perm_min": min(vals_perm),
        "perm_max": max(vals_perm),
        "perm_media": statistics.fmean(vals_perm),
        "perm_sd": statistics.pstdev(vals_perm) if len(vals_perm) > 1 else 0.0,
        "aleatorio_min": min(aleatorias),
        "aleatorio_max": max(aleatorias),
        "aleatorio_media": statistics.fmean(aleatorias),
        "aleatorio_sd": statistics.pstdev(aleatorias) if len(aleatorias) > 1 else 0.0,
        "aleatorio_valores": aleatorias,
    }


def bootstrap_ic(valores: list[float], confianza: float = 0.95, remuestreos: int = 5000,
                 semilla: int = 12345) -> tuple[float, float]:
    """Intervalo de confianza por bootstrap para la media de ``valores``.

    Devuelve ``(límite_inferior, límite_superior)`` en porcentaje (0-100).
    """
    if not valores:
        return (0.0, 0.0)
    rng = random.Random(semilla)
    n = len(valores)
    medias = []
    for _ in range(remuestreos):
        muestra = [valores[rng.randrange(n)] for _ in range(n)]
        medias.append(statistics.fmean(muestra))
    medias.sort()
    alfa = (1.0 - confianza) / 2.0
    inferior = medias[int(alfa * remuestreos)]
    superior = medias[min(remuestreos - 1, int((1.0 - alfa) * remuestreos))]
    return (inferior * 100.0, superior * 100.0)
