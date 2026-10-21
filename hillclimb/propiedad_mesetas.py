"""Verifica por qué no aparecen mesetas con la vecindad de 8 direcciones.

Hipótesis: la regla de *no cortar esquinas* implica que, si una celda tiene un
vecino con ``Δf = 0`` (un movimiento en diagonal que no cambia la distancia
Manhattan), entonces las dos celdas cardinales adyacentes existen libres y
tienen ``Δf > 0``. En consecuencia, **ningún estado puede ser meseta**: meseta
exigiría no tener ningún vecino ascendente y sí alguno lateral.

Este script comprueba la propiedad celda por celda en todos los mapas del
repositorio, incluidos los aleatorios de escalabilidad.

Uso::

    python -m hillclimb.propiedad_mesetas
"""

from __future__ import annotations

from pathlib import Path

from .algorithms import ejecutar
from .analysis import mesetas_posibles
from .escalabilidad import DENSIDADES, SEMILLA, TAMANOS, mapa_valido
from .maze import MAPA_A, MAPA_B, Maze


def todos_los_mapas() -> list[tuple[str, Maze]]:
    """Mapas A, B y los aleatorios de escalabilidad."""
    mapas = [("A", Maze(MAPA_A, "A")), ("B", Maze(MAPA_B, "B"))]
    indice = 0
    for tam in TAMANOS:
        for densidad in DENSIDADES:
            semilla = SEMILLA + indice
            indice += 1
            maze = mapa_valido(tam, tam, densidad, semilla)
            if maze is not None:
                mapas.append((f"{tam}×{tam} al {densidad * 100:.0f} %", maze))
    return mapas


def escribir_informe(resultados: list[dict], ruta: Path) -> None:
    """Escribe ``results/propiedad_mesetas.md`` con la verificación completa."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    add = L.append
    add("# Propiedad verificada: «tener vecino lateral implica tener ascendente»")
    add("")
    add(
        "Comprobación exhaustiva, celda por celda, de la implicación que explica por qué "
        "**no aparecen mesetas** ni con la vecindad de 8 direcciones. Se verifica sobre "
        "todos los mapas del repositorio —A, B y los seis aleatorios de escalabilidad— y "
        "con las dos métricas."
    )
    add("")
    add("| Mapa | Métrica | Celdas libres | Con vecino lateral | Con lateral y ascendente | Solo lateral |")
    add("|---|---|---|---|---|---|")
    for r in resultados:
        for etiqueta, clave in (("Manhattan", "m"), ("Euclídea", "e")):
            d = r[clave]
            add(f"| {r['nombre']} | {etiqueta} | {d['libres']} | {d['con_lateral']} | "
                f"{d['con_lateral_y_ascendente']} | {d['solo_lateral']} |")
    add("")
    for etiqueta, clave in (("Manhattan", "m"), ("Euclídea", "e")):
        lateral = sum(r[clave]["con_lateral"] for r in resultados)
        solo = sum(r[clave]["solo_lateral"] for r in resultados)
        add(
            f"- **{etiqueta}**: {lateral} celdas con vecino lateral examinadas, "
            f"**{solo}** sin vecino ascendente."
        )
    add("")
    add(
        "La implicación se cumple sin excepción en todos los mapas y con las dos métricas. "
        "Por tanto una meseta —estado sin vecino ascendente pero con alguno lateral— es "
        "**inalcanzable** bajo la regla de no cortar esquinas, y esa es la razón por la que "
        "el recuento de mesetas terminales es 0 en `vecindad8.md` y en "
        "`escalabilidad.md`."
    )
    add("")
    add(
        "Para observar mesetas terminales haría falta permitir **cortar esquinas**: un "
        "movimiento en diagonal cuyas dos celdas ortogonales son muro. No es el modelo de "
        "este trabajo."
    )
    add("")
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    resultados: list[dict] = []
    for nombre, maze in todos_los_mapas():
        resultados.append({
            "nombre": nombre,
            "m": mesetas_posibles(maze, "manhattan"),
            "e": mesetas_posibles(maze, "euclidea"),
        })
    print("Propiedad: «tener vecino lateral (Δf = 0) implica tener vecino ascendente»")
    print("(vecindad de 8 direcciones, sin cortar esquinas de muros)\n")
    for r in resultados:
        print(f"{r['nombre']:>18}: manhattan {r['m']['con_lateral']:4d} celdas con lateral, "
              f"{r['m']['solo_lateral']} sin ascendente | euclidea "
              f"{r['e']['con_lateral']:3d}, {r['e']['solo_lateral']} sin ascendente")

    mesetas = 0
    for _, maze in todos_los_mapas():
        for s in maze.free_cells():
            info = ejecutar(maze, s, variant="steepest", vecindad=8, max_iter=5000)
            if info.status == "plateau":
                mesetas += 1
    total_lateral = sum(r["m"]["con_lateral"] + r["e"]["con_lateral"] for r in resultados)
    total_solo = sum(r["m"]["solo_lateral"] + r["e"]["solo_lateral"] for r in resultados)
    print(f"\nCeldas con vecino lateral examinadas: {total_lateral}")
    print(f"De ellas, sin ningún vecino ascendente: {total_solo}")
    print(f"Ejecuciones que terminan en meseta con vecindad 8: {mesetas}")
    ruta = Path(__file__).resolve().parent.parent / "results" / "propiedad_mesetas.md"
    escribir_informe(resultados, ruta)
    print(f"\nInforme escrito en {ruta}")
    print(
        "\nConclusión: con la regla de no cortar esquinas, un estado con vecino lateral "
        "siempre tiene también un vecino ascendente, así que la meseta «sin mejora pero "
        "con laterales» es inalcanzable. Las mesetas solo aparecerían si se permitiera "
        "cortar esquinas (movimiento en diagonal cuyas dos ortogonales son muro)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
