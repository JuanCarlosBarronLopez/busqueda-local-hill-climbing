"""Verificación independiente de las cifras que publica el benchmark.

Reimplementa Steepest-Ascent, las cuencas de atracción y A* **sin importar**
nada de ``hillclimb.algorithms`` (solo se reusa la definición textual de los
mapas), para poder contrastar los números publicados contra una segunda
implementación escrita al calor de la auditoría.

Uso::

    python tools/verificacion_independiente.py            # MAPA_B
    python tools/verificacion_independiente.py --mapa A B  # varios mapas
"""

from __future__ import annotations

import argparse
import heapq
import sys
from pathlib import Path

# Solo se importan los mapas (datos), nunca la lógica del paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hillclimb.maze import MAPA_A, MAPA_B  # noqa: E402

ORDEN_FIJO = [("↑", -1, 0), ("↓", 1, 0), ("←", 0, -1), ("→", 0, 1)]


# ------------------------------------------------------------------ modelo propio
class Rejilla:
    """Rejilla mínima: muros, libres, meta y vecindario de 4 direcciones."""

    def __init__(self, filas: tuple[str, ...]) -> None:
        self.muros: set[tuple[int, int]] = set()
        self.meta: tuple[int, int] = (0, 0)
        self.inicio: tuple[int, int] = (0, 0)
        self.R = len(filas)
        self.C = len(filas[0].split())
        for r, fila in enumerate(filas):
            for c, ch in enumerate(fila.split()):
                if ch == "#":
                    self.muros.add((r, c))
                elif ch == "G":
                    self.meta = (r, c)
                elif ch == "S":
                    self.inicio = (r, c)

    def libre(self, celda: tuple[int, int]) -> bool:
        r, c = celda
        return (
            0 <= r < self.R
            and 0 <= c < self.C
            and (r, c) not in self.muros
        )

    def libres(self) -> list[tuple[int, int]]:
        return [
            (r, c)
            for r in range(self.R)
            for c in range(self.C)
            if (r, c) not in self.muros
        ]

    def vecinos(self, celda: tuple[int, int]) -> list[tuple[str, tuple[int, int]]]:
        r, c = celda
        return [
            (a, (r + dr, c + dc))
            for a, dr, dc in ORDEN_FIJO
            if self.libre((r + dr, c + dc))
        ]

    def d(self, celda: tuple[int, int]) -> int:
        """Distancia de Manhattan a la meta."""
        return abs(celda[0] - self.meta[0]) + abs(celda[1] - self.meta[1])

    def f(self, celda: tuple[int, int]) -> int:
        return -self.d(celda)


# ------------------------------------------------------- steepest propio (receta)
def steepest(rejilla: Rejilla, inicio: tuple[int, int], max_iter: int = 5000) -> dict:
    """Steepest-Ascent propio: vecino de mayor Δf, empate por orden fijo."""
    actual = inicio
    movimientos = 0
    visitadas = [actual]
    for it in range(1, max_iter + 1):
        if actual == rejilla.meta:
            return {
                "status": "goal",
                "final": actual,
                "movimientos": movimientos,
                "iteraciones": it,
                "camino": visitadas,
            }
        vecinos = rejilla.vecinos(actual)
        if not vecinos:
            return {"status": "local_max", "final": actual, "movimientos": movimientos,
                    "iteraciones": it, "camino": visitadas}
        mejor, mejor_delta = None, 0.0  # se exige Δf > 0 estricto
        for _, s in vecinos:
            delta = rejilla.f(s) - rejilla.f(actual)
            if delta > mejor_delta:  # '>' estricto: empate gana el primero
                mejor, mejor_delta = s, delta
        if mejor is None:
            return {"status": "local_max", "final": actual, "movimientos": movimientos,
                    "iteraciones": it, "camino": visitadas}
        actual = mejor
        movimientos += 1
        visitadas.append(actual)
    return {"status": "max_iter", "final": actual, "movimientos": movimientos,
            "iteraciones": max_iter, "camino": visitadas}


def cuencas(rejilla: Rejilla) -> dict[tuple[int, int], list[tuple[int, int]]]:
    """Cuenca de atracción del steepest propio desde cada celda libre."""
    cuencas: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for s in rejilla.libres():
        res = steepest(rejilla, s)
        cuencas.setdefault(res["final"], []).append(s)
    return cuencas


# ------------------------------------------------------------------ A* propio
def astar(rejilla: Rejilla) -> dict:
    """A* propio con heurística de Manhattan y coste uniforme 1."""
    inicio, meta = rejilla.inicio, rejilla.meta
    g: dict[tuple[int, int], int] = {inicio: 0}
    frontera: list[tuple[int, int, tuple[int, int]]] = [(rejilla.d(inicio), 0, inicio)]
    max_frontera = 1
    expandidos = 0
    while frontera:
        _, gc, s = heapq.heappop(frontera)
        if gc > g.get(s, -1):
            continue
        expandidos += 1
        if s == meta:
            return {"exito": True, "nodos_expandidos": expandidos,
                    "max_frontera": max_frontera, "longitud_camino": gc}
        for _, t in rejilla.vecinos(s):
            ng = gc + 1
            if ng < g.get(t, 10**9):
                g[t] = ng
                heapq.heappush(frontera, (ng + rejilla.d(t), ng, t))
                max_frontera = max(max_frontera, len(frontera))
    return {"exito": False, "nodos_expandidos": expandidos,
            "max_frontera": max_frontera, "longitud_camino": None}


# ---------------------------------------------------------------------- informe
def auditar(nombre: str, filas: tuple[str, ...]) -> dict:
    rejilla = Rejilla(filas)
    total = len(rejilla.libres())
    cuencas_rejilla = cuencas(rejilla)
    a_meta = sorted(cuencas_rejilla.get(rejilla.meta, []))
    p = len(a_meta) / total
    sumideros = sorted(
        (celda, len(v)) for celda, v in cuencas_rejilla.items() if celda != rejilla.meta
    )
    ruta = astar(rejilla)
    desde_s = steepest(rejilla, rejilla.inicio)
    return {
        "nombre": nombre,
        "libres": total,
        "exito": len(a_meta),
        "p": p,
        "estancamiento": 1.0 - p,
        "sumideros": sumideros,
        "meta": rejilla.meta,
        "inicio": rejilla.inicio,
        "astar": ruta,
        "desde_s": desde_s,
    }


def imprimir(info: dict) -> None:
    print(f"=== Mapa {info['nombre']} (verificación independiente) ===")
    print(f"  celdas libres |F|        : {info['libres']}")
    print(f"  cuenca de la meta |B(g)| : {info['exito']}")
    print(f"  p = |B(g)|/|F|           : {info['p']:.4f} ({info['p'] * 100:.2f} %)")
    print(f"  estancamiento 1 - p      : {info['estancamiento']:.4f} "
          f"({info['estancamiento'] * 100:.2f} %)")
    for celda, n in info["sumideros"]:
        print(f"  sumidero {celda}: {n} celdas")
    print(f"  A*: éxito={info['astar']['exito']} "
          f"nodos={info['astar']['nodos_expandidos']} "
          f"frontera_máx={info['astar']['max_frontera']} "
          f"camino={info['astar']['longitud_camino']}")
    d = info["desde_s"]
    print(f"  steepest desde S={info['inicio']}: {d['status']} en "
          f"{d['movimientos']} movimientos ({d['iteraciones']} iteraciones), "
          f"termina en {d['final']}")
    if d["status"] == "goal":
        print(f"    camino: {d['camino']}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapa", nargs="*", default=["B"], choices=["A", "B"],
                        help="mapas a verificar")
    args = parser.parse_args(argv)
    disponibles = {"A": MAPA_A, "B": MAPA_B}
    resultados = [auditar(n, disponibles[n]) for n in args.mapa]
    for info in resultados:
        imprimir(info)

    # Comparación explícita con las cifras que publica el benchmark.
    print("=== Comparación con results/tabla_metricas.md ===")
    ruta = Path(__file__).resolve().parent.parent / "results" / "tabla_metricas.md"
    if not ruta.exists():
        print("  (no hay resultados publicados todavía: ejecuta el benchmark)")
        return 0
    lineas = ruta.read_text(encoding="utf-8").strip().splitlines()
    cabecera = [c.strip() for c in lineas[0].strip("|").split("|")]
    try:
        idx_exito = cabecera.index("Tasa de éxito (%)")
    except ValueError:
        idx_exito = 3  # formato antiguo sin columna Métrica
    for linea in lineas[2:]:
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if len(celdas) <= idx_exito or celdas[0] not in ("A", "B"):
            continue
        if "steepest (ascenso" in celdas[2] or celdas[1].startswith("HC steepest"):
            indep = next(r for r in resultados if r["nombre"] == celdas[0])
            publicada = celdas[idx_exito]
            propia = f"{indep['p'] * 100:.2f}"
            coincide = abs(float(publicada) - indep["p"] * 100) < 0.005
            print(f"  {celdas[0]} · steepest: publicada {publicada} % | "
                  f"propia {propia} % | coincidencia: "
                  f"{'SÍ' if coincide else 'NO'}")
            print(f"    celdas libres: publicadas {celdas[3]} | propias {indep['libres']} "
                  f"| coincidencia: "
                  f"{'SÍ' if int(celdas[3]) == indep['libres'] else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
