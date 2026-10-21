"""Modelo del laberinto: cuadrícula 2D, vecindario y función de aptitud.

Un estado ``s`` es una celda libre ``(fila, columna)``. La vecindad ``N(s)``
son las 4 celdas libres adyacentes (sin diagonales) exploradas en orden FIJO
``↑ ↓ ← →``; ese orden hace que las variantes deterministas sean reproducibles
y que el desempate sea estable. La aptitud (a maximizar) es el negativo de la
distancia de ``s`` a la meta ``g``.
"""

from __future__ import annotations

import math
from typing import Sequence

Cell = tuple[int, int]

#: Orden fijo de exploración del vecindario (constante inmutable).
MOVES: tuple[tuple[str, int, int], ...] = (
    ("↑", -1, 0),  # arriba
    ("↓", 1, 0),  # abajo
    ("←", 0, -1),  # izquierda
    ("→", 0, 1),  # derecha
)

#: Vecindad de 8 direcciones: las 4 cardinales en su orden canónico y luego las
#: 4 diagonales, también en sentido horario (constante inmutable).
MOVES_8: tuple[tuple[str, int, int], ...] = MOVES + (
    ("↗", -1, 1),  # arriba-derecha
    ("↘", 1, 1),  # abajo-derecha
    ("↙", 1, -1),  # abajo-izquierda
    ("↖", -1, -1),  # arriba-izquierda
)

#: Vecindades válidas.
VECINDADES = (4, 8)

#: Mapas de prueba del trabajo (7 × 9; S = inicio, G = meta, # = muro).
#: Se guardan como tuplas (globales inmutables): cada ``Maze`` hace su propia copia.
MAPA_A: tuple[str, ...] = (  # Caso A: sin trampas cóncavas -> no existe ningún máximo local
    "S . . . . . . . .",
    ". . # . . . . . .",
    ". . . . # . . # .",
    ". . . . . . . . .",
    ". # . . . . # . .",
    ". . . . . . . . .",
    ". . . . . . . . G",
)

MAPA_B: tuple[str, ...] = (  # Caso B: recinto en U con la abertura mirando lejos de la meta
    ". . . . . . . . .",
    ". . # # # # # . .",
    ". . . . . . # . .",
    ". . . . S . # . G",
    ". . . . . . # . .",
    ". . # # # # # . .",
    ". . . . . . . . .",
)

#: Mapa semilla del laberinto personalizado (editable desde la GUI).
MAPA_PERSONALIZADO: tuple[str, ...] = MAPA_B


def cargar_mapa(nombre: str) -> Maze:
    """Devuelve una copia fresca del mapa ``A``, ``B`` o ``Personalizado``."""
    clave = nombre.strip().lower()
    if clave.startswith("a"):
        return Maze(MAPA_A, "Caso A: convergencia exitosa")
    if clave.startswith("b"):
        return Maze(MAPA_B, "Caso B: trampa en U")
    return Maze(MAPA_PERSONALIZADO, "Personalizado")


class Maze:
    """Laberinto en cuadrícula con muros, celda inicial ``S`` y meta ``G``."""

    def __init__(self, rows: Sequence[str], name: str = "") -> None:
        self.name = name
        self.grid: list[list[str]] = [row.split() for row in rows]
        self.R, self.C = len(self.grid), len(self.grid[0])
        if any(len(fila) != self.C for fila in self.grid):
            raise ValueError("Todas las filas del mapa deben tener el mismo número de columnas")
        self.start: Cell | None = None
        self.goal: Cell | None = None
        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                if ch == "S":
                    self.start = (r, c)
                elif ch == "G":
                    self.goal = (r, c)
        if self.start is None or self.goal is None:
            raise ValueError("El mapa necesita una S y una G")

    # ----------------------------------------------------------------- consultas
    def is_free(self, cell: Cell) -> bool:
        """¿Existe la celda y no es muro?"""
        r, c = cell
        return 0 <= r < self.R and 0 <= c < self.C and self.grid[r][c] != "#"

    def free_cells(self) -> list[Cell]:
        """Lista de todas las celdas libres (incluye S y G)."""
        return [
            (r, c)
            for r in range(self.R)
            for c in range(self.C)
            if self.grid[r][c] != "#"
        ]

    def neighbors(
        self,
        cell: Cell,
        vecindad: int = 4,
        orden: tuple[tuple[str, int, int], ...] | None = None,
    ) -> list[tuple[str, Cell]]:
        """``N(s)``: pares ``(flecha, celda)`` de vecinos libres.

        Con ``vecindad=4`` se exploran las cardinales en orden ↑ ↓ ← →; con
        ``vecindad=8`` se añaden las diagonales al final. Los movimientos
        diagonales **no cortan esquinas**: solo se admiten si las dos celdas
        ortogonales adyacentes también están libres.

        ``orden`` permite pasar una permutación concreta de las direcciones
        (para los experimentos de sensibilidad al desempate); si se indica,
        tiene prioridad sobre ``vecindad``.
        """
        if orden is None:
            if vecindad not in VECINDADES:
                raise ValueError(f"Vecindad desconocida: {vecindad!r} (use 4 u 8)")
            moves = MOVES_8 if vecindad == 8 else MOVES
        else:
            moves = orden
        r, c = cell
        out: list[tuple[str, Cell]] = []
        for arrow, dr, dc in moves:
            t = (r + dr, c + dc)
            if not self.is_free(t):
                continue
            if dr != 0 and dc != 0:
                # No cortar esquinas: ambas ortogonales adyacentes libres.
                if not (self.is_free((r + dr, c)) and self.is_free((r, c + dc))):
                    continue
            out.append((arrow, t))
        return out

    def h(self, cell: Cell, metric: str = "manhattan") -> float:
        """Distancia de ``cell`` a la meta (Manhattan o Euclidiana)."""
        dr, dc = abs(cell[0] - self.goal[0]), abs(cell[1] - self.goal[1])  # type: ignore[index]
        if metric == "manhattan":
            return float(dr + dc)
        if metric in ("euclidea", "euclidean"):
            return math.hypot(dr, dc)
        raise ValueError(f"Métrica desconocida: {metric!r}")

    def f(self, cell: Cell, metric: str = "manhattan") -> float:
        """Aptitud a maximizar: ``f(s) = -d(s, g)``; el óptimo global es ``f(g) = 0``."""
        return -self.h(cell, metric)

    def to_rows(self) -> list[str]:
        """Devuelve el laberinto como filas de texto (formato de los mapas)."""
        return [" ".join(fila) for fila in self.grid]

    def copy(self) -> Maze:
        """Copia independiente del laberinto."""
        return Maze(self.to_rows(), self.name)

    # ----------------------------------------------------------------- edición (GUI)
    def toggle_wall(self, cell: Cell) -> bool:
        """Alterna muro/libre en una celda del tablero que no sea S ni G."""
        r, c = cell
        if not (0 <= r < self.R and 0 <= c < self.C):
            return False
        if (r, c) in (self.start, self.goal):
            return False
        self.grid[r][c] = "." if self.grid[r][c] == "#" else "#"
        return True

    def set_start(self, cell: Cell) -> bool:
        """Mueve la celda inicial S a ``cell`` (debe ser libre y distinta de G)."""
        if not self.is_free(cell) or cell == self.goal:
            return False
        if self.start is not None:
            self.grid[self.start[0]][self.start[1]] = "."
        self.grid[cell[0]][cell[1]] = "S"
        self.start = cell
        return True
