"""A* con la misma heurística, como contraste de memoria frente a Hill Climbing.

No forma parte de la práctica de búsqueda local: sirve para evidenciar la
diferencia de costo en memoria. Hill Climbing guarda un único estado
(memoria O(1)); A* necesita la frontera y los costes acumulados, de modo que
su memoria crece con el número de nodos generados.
"""

from __future__ import annotations

import heapq
import time

from .maze import Cell, Maze


def astar(maze: Maze, metric: str = "manhattan") -> dict:
    """Ejecuta A* desde S hasta G y devuelve sus métricas de expansión y memoria."""
    start, goal = maze.start, maze.goal
    if start is None or goal is None:  # pragma: no cover - Maze ya lo valida
        raise ValueError("El laberinto necesita S y G")
    g: dict[Cell, int] = {start: 0}
    # Entradas (f, g, celda): el orden de la tupla hace determinista el desempate.
    frontera: list[tuple[float, int, Cell]] = [(maze.h(start, metric), 0, start)]
    max_frontera = 1
    expandidos = 0
    while frontera:
        f, gc, s = heapq.heappop(frontera)
        if gc > g.get(s, -1):
            continue  # entrada obsoleta
        expandidos += 1
        if s == goal:
            return {
                "nodos_expandidos": expandidos,
                "max_frontera": max_frontera,
                "longitud_camino": gc,
                "exito": True,
            }
        for _, t in maze.neighbors(s):
            ng = gc + 1
            if ng < g.get(t, float("inf")):
                g[t] = ng
                heapq.heappush(frontera, (ng + maze.h(t, metric), ng, t))
                max_frontera = max(max_frontera, len(frontera))
    return {
        "nodos_expandidos": expandidos,
        "max_frontera": max_frontera,
        "longitud_camino": None,
        "exito": False,
    }


def ejecutar_astar(maze: Maze, metric: str = "manhattan") -> dict:
    """Igual que :func:`astar` pero cronometrado con ``time.perf_counter_ns``."""
    t0 = time.perf_counter_ns()
    datos = astar(maze, metric)
    datos["tiempo_ms"] = (time.perf_counter_ns() - t0) / 1e6
    return datos
