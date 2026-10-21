"""Modo consola paso a paso.

Ejemplo::

    python -m hillclimb.cli --mapa B --variante steepest --paso

Imprime la misma telemetría que la GUI y espera ``Enter`` en cada iteración.
La lógica del algoritmo NO vive aquí: solo se consume el generador
:func:`hillclimb.algorithms.hill_climbing` (o :func:`random_restart`).
"""

from __future__ import annotations

import argparse
import random
import sys

from .algorithms import ETIQUETAS, StepInfo, hill_climbing, random_restart
from .maze import Maze, cargar_mapa

METRICAS = ("manhattan", "euclidea")


def _configurar_salida() -> None:
    """Hace que la salida por consola tolere caracteres no ASCII.

    Sin esto, en una consola Windows con codificación cp1252 los símbolos
    `↑`, `Δ`, `λ` o `…` producen ``UnicodeEncodeError`` y la CLI se cae.
    """
    for atributo in ("reconfigure",):
        funcion = getattr(sys.stdout, atributo, None)
        if callable(funcion):
            try:
                funcion(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - salida no reconfigurable
                pass


def _fmt(valor: float) -> str:
    """Dos decimales, normalizando el ``-0.0`` que produce ``f(g) = 0``."""
    return f"{valor if valor != 0.0 else 0.0:.2f}"


def formatear_paso(info: StepInfo) -> str:
    """Telemetría de una iteración en texto (formato compartido con la GUI)."""
    lineas = [f"Iteración {info.iteration} | Estado: {info.current} | f = {_fmt(info.f_current)}"]
    if info.restart:
        lineas[0] += f" | Reinicio: {info.restart}"
    lineas[0] += f" | Movimientos: {info.moves}"
    for e in info.evaluations:
        marca = "  <= elegido" if info.chosen == e.cell else ""
        lineas.append(
            f"  {e.arrow} {e.cell}  f = {_fmt(e.f)}  Δf = {e.delta:+.2f}{marca}"
        )
    if info.decision:
        lineas.append(f"Decisión: {info.decision}")
    if info.status != "running":
        lineas.append(f"Resultado: {ETIQUETAS[info.status]}")
    return "\n".join(lineas)


def _construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m hillclimb.cli",
        description="Hill Climbing sobre un laberinto con trampas cóncavas (modo consola).",
    )
    p.add_argument("--mapa", choices=["A", "B"], default="A", help="mapa de prueba")
    p.add_argument(
        "--variante", default="steepest",
        choices=["simple", "steepest", "stochastic", "first_choice"],
        help="variante de Hill Climbing",
    )
    p.add_argument("--metrica", choices=list(METRICAS), default="manhattan",
                   help="métrica de distancia para f(s) = -d(s, g)")
    p.add_argument("--vecindad", type=int, choices=(4, 8), default=4,
                   help="número de direcciones de N(s) (8 incluye diagonales sin "
                        "cortar esquinas)")
    p.add_argument("--desempate", choices=("fijo", "aleatorio"), default="fijo",
                   help="desempate del steepest ante empates en Δf")
    p.add_argument("--laterales", type=int, default=0,
                   help="movimientos laterales permitidos (0 = desactivados)")
    p.add_argument("--penalizacion", type=float, default=0.0,
                   help="lambda de la penalización por estancamiento (0 = desactivada)")
    p.add_argument("--reinicios", type=int, default=0,
                   help="máximo de reinicios aleatorios (0 = desactivados)")
    p.add_argument("--semilla", type=int, default=None,
                   help="semilla del generador aleatorio (reproducibilidad)")
    p.add_argument("--max-iter", type=int, default=5000, help="límite de iteraciones")
    p.add_argument("--paso", action="store_true",
                   help="pausa tras cada iteración esperando Enter")
    p.add_argument("--auto", action="store_true",
                   help="imprime todo sin pausas (comportamiento por defecto)")
    return p


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI."""
    _configurar_salida()
    args = _construir_parser().parse_args(argv)
    maze: Maze = cargar_mapa(args.mapa)
    rng = random.Random(args.semilla)

    kw = dict(
        variant=args.variante,
        metric=args.metrica,
        vecindad=args.vecindad,
        desempate=args.desempate,
        sideways_limit=max(args.laterales, 0),
        penalty_lambda=max(args.penalizacion, 0.0),
        max_iter=max(args.max_iter, 1),
    )
    print(f"Mapa {args.mapa} ({maze.name}) | variante {args.variante} | "
          f"métrica {args.metrica} | vecindad {args.vecindad} | "
          f"desempate {args.desempate}")
    if maze.start is None or maze.goal is None:  # pragma: no cover - mapa interno
        print("El mapa no tiene S o G.")
        return 1
    print(f"Inicio S = {maze.start} | Meta G = {maze.goal} | "
          f"f(S) = {_fmt(maze.f(maze.start, args.metrica))}")
    print(f"Mitigaciones: laterales={kw['sideways_limit']}, "
          f"penalización λ={kw['penalty_lambda']}, reinicios={args.reinicios}, "
          f"semilla={args.semilla if args.semilla is not None else 'aleatoria'}")
    print("-" * 64)

    if args.reinicios > 0:
        gen = random_restart(maze, maze.start, rng, max_restarts=args.reinicios, **kw)
    else:
        gen = hill_climbing(maze, maze.start, rng=rng, **kw)

    pausa = args.paso and not args.auto
    for info in gen:
        print(formatear_paso(info))
        if pausa and info.status == "running":
            try:
                input("Presiona Enter para la siguiente iteración...")
            except EOFError:  # pragma: no cover - entrada cerrada
                break
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
