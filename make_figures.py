"""Genera las cinco figuras del reporte en ``results/figuras/``.

Uso::

    python make_figures.py

No abre la GUI: ejecuta los algoritmos y dibuja el resultado con Pillow.
"""

from __future__ import annotations

import random
from pathlib import Path

from hillclimb.algorithms import hill_climbing, random_restart
from hillclimb.analysis import barrier_depth, basin_of_attraction, basin_stats
from hillclimb.figures import camino, guardar, render
from hillclimb.maze import MAPA_A, MAPA_B, Maze

SALIDA = Path(__file__).resolve().parent / "results" / "figuras"
SEMILLA = 2024


def figura_caso_a(salida: Path) -> Path:
    """Figura 1: Caso A, camino completo hasta la meta."""
    maze = Maze(MAPA_A, "Caso A")
    infos = list(hill_climbing(maze, maze.start, variant="steepest"))
    final = infos[-1]
    img = render(
        maze,
        "Caso A — convergencia exitosa al óptimo global",
        "Steepest-Ascent, orden fijo ↑ ↓ ← →, métrica Manhattan; "
        f"{final.moves} movimientos y {final.iteration} iteraciones hasta G = (6, 8).",
        rastro=camino(infos),
        actual=maze.goal,
        pie="Sombreado más claro = más cerca de la meta. No existe ningún máximo local: "
            "la cuenca de atracción de G es el 100 % de las celdas libres.",
    )
    return guardar(img, salida / "caso_A_exito.png")


def figura_caso_b_atrapado(salida: Path) -> Path:
    """Figura 2: Caso B atrapado en (3,5) con la telemetría del último paso."""
    maze = Maze(MAPA_B, "Caso B")
    infos = list(hill_climbing(maze, maze.start, variant="steepest"))
    final = infos[-1]
    img = render(
        maze,
        "Caso B — atrapamiento en el máximo local (3, 5)",
        f"Steepest-Ascent desde S = (3, 4): {final.moves} movimiento hasta (3, 5), "
        "donde f = -3.00 y los tres vecinos libres tienen Δf = -1.00.",
        rastro=camino(infos),
        actual=final.current,
        evaluaciones=final.evaluations,
        marcas={final.current: "MÁXIMO LOCAL"},
        pie="Verde = Δf > 0, rojo = Δf < 0. La meta está a 3 pasos en línea recta, "
            "pero el muro de (3, 6) lo impide.",
    )
    return guardar(img, salida / "caso_B_atrapado.png")


def figura_caso_b_penalizacion(salida: Path) -> Path:
    """Figura 3: Caso B con penalización por estancamiento."""
    maze = Maze(MAPA_B, "Caso B")
    infos = list(
        hill_climbing(maze, maze.start, variant="steepest", penalty_lambda=1.0, max_iter=5000)
    )
    final = infos[-1]
    img = render(
        maze,
        "Caso B — escape de la trampa por penalización λ = 1",
        f"f′(s) = f(s) − n(s): {final.iteration} iteraciones, {final.moves} movimientos y "
        f"{sum(final.penalties.values())} penalizaciones hasta G.",
        rastro=camino(infos),
        actual=maze.goal,
        pie="Cada estancamiento incrementa n(s) y hunde f′(s), de modo que los vecinos "
            "antes inútiles se vuelven atractivos.",
    )
    return guardar(img, salida / "caso_B_penalizacion.png")


def figura_caso_b_reinicios(salida: Path) -> Path:
    """Figura 4: Caso B con reinicios aleatorios (intentos fallidos en tenue)."""
    maze = Maze(MAPA_B, "Caso B")
    intentos: dict[int, list[tuple[str, tuple[int, int]]]] = {}
    for info in random_restart(maze, maze.start, random.Random(SEMILLA), max_restarts=100):
        intentos.setdefault(info.restart, [])
        if info.chosen is not None:
            for e in info.evaluations:
                if e.cell == info.chosen:
                    intentos[info.restart].append((e.arrow, e.cell))
                    break
    usados = max(intentos) if intentos else 0
    fallidos = [flecha_celda for r, pasos in intentos.items() if r < usados for flecha_celda in pasos]
    exitosos = intentos.get(usados, [])
    img = render(
        maze,
        "Caso B — escape por reinicios aleatorios",
        f"Semilla fija {SEMILLA}: {usados} reinicio(s) necesarios desde S "
        f"(p = 48.00 %, 1/p = 2.08 esperados).",
        rastro=exitosos,
        rastro_tenue=fallidos,
        actual=maze.goal,
        marcas={maze.goal: "META"} if usados else None,
        pie="Gris tenue = intentos anteriores atrapados en el máximo local; "
            "azul = último intento, que alcanza la meta.",
    )
    return guardar(img, salida / "caso_B_reinicios.png")


def figura_mapa_calor(salida: Path) -> Path:
    """Figura 5: mapa de calor de f con las cuencas de atracción coloreadas."""
    maze = Maze(MAPA_B, "Caso B")
    cuencas = basin_of_attraction(maze, variant="steepest")
    stats = basin_stats(maze)
    meta = maze.goal
    sumideros = {c: len(v) for c, v in cuencas.items() if c != meta}
    prof = barrier_depth(maze, (3, 5))
    texto_sumideros = ", ".join(f"{c}: {n} celdas" for c, n in sumideros.items())
    img = render(
        maze,
        "Mapa de calor de f(s) = −d(s, g) y cuencas de atracción (mapa B)",
        f"p = {stats['exito']}/{stats['libres']} = {stats['p'] * 100:.2f} % de éxito | "
        f"estancamiento = {stats['estancamiento'] * 100:.2f} % | barrera de (3, 5) = {prof:.2f}",
        cuencas=cuencas,
        marcas={(3, 5): "MÁXIMO LOCAL"},
        pie=f"Verde = cuenca de la meta ({stats['exito']} celdas) | rojo = {texto_sumideros}. "
            "Mismo f, distinto destino: la cuenca depende del estado inicial.",
    )
    return guardar(img, salida / "mapa_calor_f_B.png")


def main() -> int:
    """ Genera las cinco figuras y devuelve 0. """
    SALIDA.mkdir(parents=True, exist_ok=True)
    rutas = [
        figura_caso_a(SALIDA),
        figura_caso_b_atrapado(SALIDA),
        figura_caso_b_penalizacion(SALIDA),
        figura_caso_b_reinicios(SALIDA),
        figura_mapa_calor(SALIDA),
    ]
    print("Figuras generadas:")
    for ruta in rutas:
        print(f"  - {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
