"""Paquete ``hillclimb``: búsqueda local por Hill Climbing sobre un laberinto 2D.

El problema modelo es el *escape de un laberinto con trampas cóncavas*: el
algoritmo asciende por la función de aptitud ``f(s) = -d(s, g)`` y puede
quedar atrapado en máximos locales, mesetas o replicar la trampa del
recinto en U.
"""

from .maze import MAPA_A, MAPA_B, Cell, Maze, cargar_mapa
from .algorithms import StepInfo, hill_climbing, random_restart
from .analysis import (
    barrier_depth,
    basin_of_attraction,
    basin_stats,
    expected_cost,
    expected_restarts,
    success_after,
)

__all__ = [
    "MAPA_A",
    "MAPA_B",
    "Cell",
    "Maze",
    "cargar_mapa",
    "StepInfo",
    "hill_climbing",
    "random_restart",
    "barrier_depth",
    "basin_of_attraction",
    "basin_stats",
    "expected_restarts",
    "success_after",
    "expected_cost",
]
