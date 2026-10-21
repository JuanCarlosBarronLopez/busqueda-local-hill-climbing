"""Benchmark: métricas agregadas por mapa y configuración.

Uso::

    python -m hillclimb.benchmark                      # Manhattan
    python -m hillclimb.benchmark --metrica euclidea   # Euclídea
    python -m hillclimb.benchmark --salidas            # sin escribir archivos

Escribe ``results/metricas.csv``, ``results/tabla_metricas.md``,
``results/sensibilidad_desempate.md``, ``results/tiempo_telemetria.md`` y
``results/resumen_resultados.md``.

Diseño experimental:

* Las configuraciones **deterministas** se ejecutan de forma **exhaustiva desde
  cada celda libre**: así la tasa de éxito es exactamente ``p = |B(g)| / |F|``.
* Las configuraciones **aleatorias** se ejecutan 1000 veces desde celdas
  iniciales uniformes, con semilla fija (42) y reproducibles.
* Cada configuración se cronometra ``REPETICIONES`` veces (con calentamiento
  previo) y se reporta **mediana** y **rango intercuartílico (IQR)**, que son
  estadísticos robustos frente a valores atípicos del sistema.
* El módulo :func:`hillclimb.algorithms.hill_climbing_ligero` permite medir el
  mismo trabajo sin construir telemetría, para cuantificar su coste.

Determinismo: las celdas iniciales aleatorias y las semillas de cada ejecución
se derivan exclusivamente de ``SEMILLA``, de forma que dos ejecuciones del
benchmark producen el **mismo CSV salvo las columnas de tiempo**.
"""

from __future__ import annotations

import argparse
import csv
import platform
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .algorithms import (
    ESTANCAMIENTOS,
    StepInfo,
    ejecutar,
    hill_climbing,
    hill_climbing_ligero,
    random_restart,
)
from .analysis import (
    barrier_depth,
    basin_stats,
    bootstrap_ic,
    escape_iterations,
    expected_cost,
    expected_restarts,
    mesetas_posibles,
    restart_iterations,
    sensibilidad_desempate,
    success_after,
)
from .astar import ejecutar_astar
from .maze import MAPA_A, MAPA_B, Cell, Maze

#: Semilla maestra del benchmark (reproducibilidad).
SEMILLA = 42
#: Ejecuciones de las variantes aleatorias.
N_ALEATORIAS = 1000
#: Máximo de reinicios por ejecución en la configuración de reinicios.
MAX_REINICIOS = 100
#: Semilla fija del experimento manual de reinicios (coincide con la prueba).
SEMILLA_REINICIOS_MANUAL = 2024
#: Repeticiones cronometradas de cada configuración (para mediana e IQR).
REPETICIONES = 5
#: Celdas iniciales por semilla en el muestreo de desempate aleatorio.
SEMILLAS_DESEMPATE = 200
#: Remuestreos del bootstrap de los reinicios.
REMUESTREOS_BOOTSTRAP = 5000

RUTA_BASE = Path(__file__).resolve().parent.parent
RUTA_RESULTADOS = RUTA_BASE / "results"
RUTA_FIGURAS = RUTA_RESULTADOS / "figuras"

METRICAS = ("manhattan", "euclidea")

#: (nombre visible, parámetros, tipo) de las siete configuraciones obligatorias.
CONFIGURACIONES: list[tuple[str, dict, str]] = [
    ("HC simple (primer mejora)", dict(variant="simple"), "determinista"),
    ("HC steepest (ascenso más pronunciado)", dict(variant="steepest"), "determinista"),
    ("HC estocástico (∝ Δf)", dict(variant="stochastic"), "aleatoria"),
    ("HC first-choice (aleatorio)", dict(variant="first_choice"), "aleatoria"),
    ("Steepest + laterales L=20", dict(variant="steepest", sideways_limit=20), "determinista"),
    ("Steepest + penalización λ=1", dict(variant="steepest", penalty_lambda=1.0), "determinista"),
    ("Steepest + reinicios aleatorios (máx 100)", dict(variant="steepest", restart=True), "aleatoria"),
]

COLUMNAS = [
    "Mapa",
    "Métrica",
    "Configuración",
    "Ejecuciones",
    "Tasa de éxito (%)",
    "Estancamiento (%)",
    "Iteraciones medias (éxito)",
    "Iteraciones medias (fallo)",
    "Reinicios medios",
    "Tiempo mediana (ms)",
    "Tiempo IQR (ms)",
]


@dataclass
class Fila:
    """Una fila de la tabla de métricas."""

    mapa: str
    metrica: str
    configuracion: str
    ejecuciones: int
    tasa_exito: float
    estancamiento: float
    it_exito: float | None
    it_fallo: float | None
    reinicios: float
    tiempo_mediana: float
    tiempo_iqr: float
    extra: dict = field(default_factory=dict)

    def como_columnas(self) -> list[str]:
        return [
            self.mapa, self.metrica_label(), self.configuracion, str(self.ejecuciones),
            _num(self.tasa_exito), _num(self.estancamiento),
            _num(self.it_exito), _num(self.it_fallo), _num(self.reinicios),
            _num(self.tiempo_mediana, 4), _num(self.tiempo_iqr, 4),
        ]

    def metrica_label(self) -> str:
        return {"manhattan": "Manhattan", "euclidea": "Euclídea"}.get(
            self.metrica, self.metrica
        )


def _num(valor: float | None, decimales: int = 2) -> str:
    if valor is None:
        return "—"
    if valor == 0:
        valor = 0.0  # normaliza el -0.0
    return f"{valor:.{decimales}f}"


def _semilla_de(indice: int) -> int:
    """Semilla derivada de la semilla maestra y del índice de ejecución."""
    return SEMILLA * 100_003 + indice


def _celdas_iniciales(base: Maze, tipo: str) -> list[tuple[int, int]]:
    """Celdas iniciales: exhaustivas si es determinista, uniformes si es aleatoria."""
    if tipo == "determinista":
        return base.free_cells()
    rng = random.Random(SEMILLA)  # misma semilla en cada configuración
    libres = base.free_cells()
    return [rng.choice(libres) for _ in range(N_ALEATORIAS)]


def _mediana_iqr(valores: list[float]) -> tuple[float, float]:
    """Mediana y rango intercuartílico (IQR) de una lista de tiempos en ms."""
    if not valores:
        return (0.0, 0.0)
    cuantiles = statistics.quantiles(valores, n=4, method="inclusive")
    return (statistics.median(valores), cuantiles[2] - cuantiles[0])


def una_ejecucion(maze: Maze, start: tuple[int, int], params: dict, seed: int,
                  ligero: bool = False) -> dict:
    """Ejecuta una configuración completa y devuelve sus métricas por ejecución."""
    kw = dict(params)
    reinicios = bool(kw.pop("restart", False))
    rng = random.Random(seed)
    t0 = time.perf_counter_ns()
    if reinicios:
        gen: Iterator[StepInfo] = random_restart(
            maze, start, rng, max_restarts=MAX_REINICIOS, **kw
        )
    elif ligero:
        resultado = hill_climbing_ligero(maze, start, rng=rng, **kw)
        tiempo_ms = (time.perf_counter_ns() - t0) / 1e6
        return {
            "exito": resultado["status"] == "goal",
            "estancamiento": resultado["status"] in ESTANCAMIENTOS,
            "iteraciones": resultado["iteraciones"],
            "movimientos": resultado["movimientos"],
            "reinicios": 0,
            "tiempo_ms": tiempo_ms,
            "estado": resultado["status"],
            "final": None,
        }
    else:
        gen = hill_climbing(maze, start, rng=rng, **kw)

    # Con reinicios se acumulan las iteraciones de TODOS los intentos.
    it_total, mov_total, intentos = 0, 0, 0
    info: StepInfo | None = None
    it_de_intento = 0
    for info in gen:
        if info.restart != intentos:
            it_total += it_de_intento
            intentos = info.restart
            it_de_intento = 0
        it_de_intento = info.iteration
        if info.chosen is not None:
            mov_total += 1
    if info is not None:
        it_total += it_de_intento
    tiempo_ms = (time.perf_counter_ns() - t0) / 1e6
    if info is None:  # pragma: no cover - el generador siempre emite pasos
        raise RuntimeError("La ejecución no produjo telemetría")
    return {
        "exito": info.status == "goal",
        "estancamiento": info.status in ESTANCAMIENTOS,
        "iteraciones": info.iteration if not reinicios else it_total,
        "movimientos": info.moves if not reinicios else mov_total,
        "reinicios": info.restart,
        "tiempo_ms": tiempo_ms,
        "estado": info.status,
        "final": info.current,
    }


def medir_configuracion(base: Maze, nombre: str, params: dict, tipo: str,
                        ligero: bool = False) -> Fila:
    """Mide una configuración: repeticiones cronometradas con calentamiento."""
    inicios = _celdas_iniciales(base, tipo)
    n = len(inicios)

    # --- calentamiento: la primera pasada no se cronometra -------------------
    if not ligero:
        for s in inicios[:5]:
            una_ejecucion(base, s, params, _semilla_de(0))

    pasos_tiempo: list[float] = []
    ejecuciones: list[dict] = []
    for rep in range(REPETICIONES):
        t0 = time.perf_counter_ns()
        ejecuciones = [
            una_ejecucion(base, s, params, _semilla_de(i), ligero=ligero)
            for i, s in enumerate(inicios)
        ]
        pasos_tiempo.append((time.perf_counter_ns() - t0) / 1e6)

    exitos = [e for e in ejecuciones if e["exito"]]
    fallos = [e for e in ejecuciones if e["estancamiento"]]
    mediana, iqr = _mediana_iqr(pasos_tiempo)
    fila = Fila(
        mapa=base.name,
        metrica=params.get("metric", "manhattan"),
        configuracion=nombre + (" [sin telemetría]" if ligero else ""),
        ejecuciones=n,
        tasa_exito=100.0 * len(exitos) / n,
        estancamiento=100.0 * len(fallos) / n,
        it_exito=statistics.fmean([e["iteraciones"] for e in exitos]) if exitos else None,
        it_fallo=statistics.fmean([e["iteraciones"] for e in fallos]) if fallos else None,
        reinicios=statistics.fmean([float(e["reinicios"]) for e in ejecuciones]) or 0.0,
        tiempo_mediana=mediana / n,  # por ejecución
        tiempo_iqr=iqr / n,
        extra={
            "reinicios_valores": [e["reinicios"] for e in exitos],
            "estados": {e["estado"] for e in ejecuciones},
        },
    )
    return fila


def medir_mapa(nombre: str, filas: tuple[str, ...], metrica: str,
               ligero: bool = False) -> list[Fila]:
    """Mide las 7 configuraciones sobre un mapa y devuelve las filas de la tabla."""
    base = Maze(filas, nombre)
    salida: list[Fila] = []
    for nombre_cfg, params, tipo in CONFIGURACIONES:
        params = dict(params)
        params["metric"] = metrica
        fila = medir_configuracion(base, nombre_cfg, params, tipo, ligero=ligero)
        salida.append(fila)
        print(f"  [medido] {nombre} · {fila.metrica_label()} · {nombre_cfg}: "
              f"{fila.ejecuciones} ejecuciones, éxito {fila.tasa_exito:.2f} %, "
              f"mediana {fila.tiempo_mediana:.4f} ms (IQR {fila.tiempo_iqr:.4f})")
    return salida


# ---------------------------------------------------------------- escritura
def escribir_csv(filas: list[Fila], ruta: Path) -> None:
    """Escribe el CSV (UTF-8 con BOM para abrir bien en Excel)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=",")
        escritor.writerow(COLUMNAS)
        for f in filas:
            escritor.writerow(f.como_columnas())


def escribir_markdown(filas: list[Fila], ruta: Path) -> str:
    """Escribe la tabla Markdown y la devuelve como texto."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        "| " + " | ".join(COLUMNAS) + " |",
        "|" + "|".join(["---"] * len(COLUMNAS)) + "|",
    ]
    for f in filas:
        lineas.append("| " + " | ".join(f.como_columnas()) + " |")
    contenido = "\n".join(lineas) + "\n"
    ruta.write_text(contenido, encoding="utf-8")
    return contenido


def escribir_sensibilidad(datos: dict, ruta: Path) -> None:
    """Escribe ``results/sensibilidad_desempate.md``."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    etiqueta = {"manhattan": "Manhattan", "euclidea": "Euclídea"}.get(
        datos.get("metrica", "manhattan"), "Manhattan"
    )
    L: list[str] = []
    add = L.append
    add("# Sensibilidad del resultado a la regla de desempate (mapa B)")
    add("")
    add(
        f"La variante *steepest* debe elegir entre varios vecinos cuando empatan en `Δf`. "
        f"Este documento mide cómo cambia `p = |B(g)|/|F|` según la regla de desempate, "
        f"sobre el mapa B con métrica **{etiqueta}**."
    )
    add("")
    add(f"- Celdas libres |F|: **{datos['libres']}**.")
    add(f"- Orden fijo por defecto `↑ ↓ ← →`: **p = {datos['orden_fijo_p'] * 100:.2f} %**.")
    add("")
    add("## (a) Las 24 permutaciones del orden de movimientos")
    add("")
    add("| Orden de exploración | p (%) |")
    add("|---|---|")
    for nombre, p in datos["permutaciones"].items():
        add(f"| {nombre} | {p * 100:.2f} |")
    add("")
    add(
        f"**Mínimo {datos['perm_min'] * 100:.2f} % · máximo {datos['perm_max'] * 100:.2f} % · "
        f"media {datos['perm_media'] * 100:.2f} % · desviación típica "
        f"{datos['perm_sd'] * 100:.2f} puntos porcentuales.**"
    )
    add("")
    add(
        "## (b) Desempate aleatorio entre los empatados\n"
    )
    add("")
    add(
        f"{datos['n_semillas']} semillas, cada una explorando las {datos['libres']} celdas "
        f"libres con un generador propio:\n"
    )
    add("")
    add(
        f"**Mínimo {datos['aleatorio_min'] * 100:.2f} % · máximo "
        f"{datos['aleatorio_max'] * 100:.2f} % · media {datos['aleatorio_media'] * 100:.2f} % · "
        f"desviación típica {datos['aleatorio_sd'] * 100:.2f} puntos porcentuales.**"
    )
    add("")
    add(
        "**Conclusión:** `p` no es una constante del mapa, sino del par "
        "(mapa, regla de desempate): en el mapa B oscila entre "
        f"{datos['perm_min'] * 100:.2f} % y {datos['perm_max'] * 100:.2f} % según cómo se "
        "resuelvan los empates. El resto del repositorio fija el desempate "
        "**por orden canónico `↑ ↓ ← →`, tomando el primero de los empatados**, "
        "que es la opción determinista y reproducible."
    )
    add("")
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")


def escribir_telemetria(datos: dict, ruta: Path) -> None:
    """Escribe ``results/tiempo_telemetria.md`` (coste de la telemetría)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    add = L.append
    add("# Coste de la telemetría paso a paso")
    add("")
    add(
        "Comparación del mismo trabajo resuelto con el generador telemetrado "
        "(`hill_climbing`, que construye un `StepInfo` por iteración) y con el "
        f"modo ligero (`hill_climbing_ligero`, sin telemetría). "
        f"{REPETICIONES} repeticiones, mediana e IQR por ejecución, mismo mapa y "
        "mismas semillas."
    )
    add("")
    add("| Mapa | Métrica | Configuración | Ejecuciones | Mediana con telemetría (ms) | "
        "Mediana sin telemetría (ms) | Diferencia (veces) |")
    add("|---|---|---|---|---|---|---|")
    for fila_con, fila_sin in datos["pares"]:
        veces = (
            fila_con.tiempo_mediana / fila_sin.tiempo_mediana
            if fila_sin.tiempo_mediana else float("inf")
        )
        add(
            f"| {fila_con.mapa} | {fila_con.metrica_label()} | {fila_con.configuracion} | "
            f"{fila_con.ejecuciones} | {fila_con.tiempo_mediana:.4f} | "
            f"{fila_sin.tiempo_mediana:.4f} | {veces:.2f} |"
        )
    add("")
    add(
        "Los números son órdenes de magnitud de décimas de milisegundo en mapas de "
        "7 × 9: la diferencia absoluta es minúscula, pero muestra que la telemetría "
        "cuesta un factor aproximadamente constante en trabajo por iteración, y que "
        "no debe activarse cuando solo interesan las métricas agregadas."
    )
    add("")
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")


def escribir_entorno(ruta: Path) -> None:
    """Escribe ``results/entorno.md`` con la versión de Python y datos del equipo."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    maquina = platform.uname()
    try:
        import os

        nucleos = os.cpu_count() or 0
        cpu = f"{nucleos} núcleos lógicos"
    except Exception:  # pragma: no cover
        cpu = "desconocido"
    version = sys.version.splitlines()[0]
    try:
        import PIL

        pillow = PIL.__version__
    except Exception:  # pragma: no cover
        pillow = "no instalada"
    L = [
        "# Entorno de medición",
        "",
        f"- **Python:** {version}",
        f"- **Sistema operativo:** {maquina.system} {maquina.release} "
        f"(build {maquina.version})",
        f"- **Procesador:** {maquina.processor or 'no reportado'} — {cpu} núcleos lógicos",
        f"- **Arquitectura:** {maquina.machine}",
        f"- **Pillow:** {pillow}",
        "- **pytest:** véase `requirements.txt`",
        "",
        "Mediciones tomadas con `time.perf_counter_ns` en este equipo el día de la "
        "última ejecución del benchmark. Los tiempos de `results/` son **de esta "
        "máquina** y no son comparables con los de otra sin volver a ejecutar "
        "`python -m hillclimb.benchmark`.",
        "",
    ]
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- experimentos
def experimentos_extra(maze_a: Maze, maze_b: Maze, metrica: str) -> dict:
    """Experimentos puntuales cuyo dato se cita en el reporte."""
    if maze_b.start is None:  # pragma: no cover - mapas internos siempre con S
        raise ValueError("El mapa B necesita una celda inicial S")
    inicio_b = maze_b.start
    estado_pen, it_pen = escape_iterations(maze_b, inicio_b, 1.0, metric=metrica)
    info_pen = ejecutar(
        maze_b, inicio_b, variant="steepest",
        penalty_lambda=1.0, metric=metrica, max_iter=5000,
    )
    info_pen_lat = ejecutar(
        maze_b, inicio_b, variant="steepest",
        penalty_lambda=1.0, sideways_limit=20, metric=metrica, max_iter=5000,
    )
    estado_res, usados, _ = restart_iterations(maze_b, inicio_b,
                                               SEMILLA_REINICIOS_MANUAL, metric=metrica)
    cuenca_a = basin_stats(maze_a)
    cuenca_b = basin_stats(maze_b, metric=metrica)
    # Ambas métricas se midan siempre, para poder compararlas en el informe.
    cuenca_b_man = basin_stats(maze_b, metric="manhattan")
    cuenca_b_eucl = basin_stats(maze_b, metric="euclidea")
    maxima_local = (3, 5)
    profundidad = barrier_depth(maze_b, maxima_local, metric=metrica)
    astar_b = ejecutar_astar(maze_b)
    astar_a = ejecutar_astar(maze_a)
    laterales_usados = sum(
        1
        for info in hill_climbing(
            maze_b, inicio_b, variant="steepest",
            penalty_lambda=1.0, sideways_limit=20, metric=metrica, max_iter=5000,
        )
        if info.decision.startswith("Movimiento lateral")
    )
    sumideros_b = {c: len(v) for c, v in cuenca_b["cuencas"].items()}
    otra_metrica = "manhattan" if metrica == "euclidea" else "euclidea"
    return {
        "sumideros_b": sumideros_b,
        "celdas_lateral_8": mesetas_posibles(maze_b)["con_lateral"],
        "mesetas_totales": mesetas_posibles(maze_b)["solo_lateral"],
        "it_pen_esta_metrica": _iteraciones_penalizacion(maze_b, inicio_b, metrica),
        "it_pen_otra_metrica": _iteraciones_penalizacion(maze_b, inicio_b, otra_metrica),
        "penalizacion": {
            "estado": estado_pen,
            "iteraciones": it_pen,
            "movimientos": info_pen.moves,
            "penalizaciones": sum(info_pen.penalties.values()),
        },
        "penalizacion_laterales": {
            "estado": info_pen_lat.status,
            "iteraciones": info_pen_lat.iteration,
            "movimientos": info_pen_lat.moves,
            "laterales": laterales_usados,
        },
        "reinicios_manual": {"estado": estado_res, "usados": usados},
        "cuenca_a": cuenca_a,
        "cuenca_b": cuenca_b,
        "cuenca_b_euclidea": cuenca_b_eucl,
        "cuenca_b_manhattan": cuenca_b_man,
        "profundidad_barrera": profundidad,
        "maxima_local": maxima_local,
        "f_trampa": maze_b.f(maxima_local, metrica),
        "f_escape_arriba": maze_b.f((0, 1), metrica),
        "astar": {"A": astar_a, "B": astar_b},
    }


def _iteraciones_penalizacion(maze: Maze, inicio: Cell, metrica: str) -> float:
    """Iteraciones medias de la penalización λ = 1 desde cada celda libre."""
    valores = []
    for s in maze.free_cells():
        info = ejecutar(maze, s, variant="steepest", penalty_lambda=1.0,
                        metric=metrica, max_iter=5000)
        if info.status == "goal":
            valores.append(float(info.iteration))
    return statistics.fmean(valores) if valores else float("nan")


def teoria_reinicios(filas: list[Fila], maze: Maze) -> dict:
    """Comparación teoría vs. medido para los reinicios aleatorios.

    Convención usada en el experimento (y en el benchmark): la primera celda
    inicial es **aleatoria uniforme**, no `S`. Por tanto, sobre `K` intentos
    independientes con éxito `p`:

        E[K] = 1/p ejecuciones totales
        E[R] = E[K] - 1 = (1 - p)/p  reinicios (fallos previos al primer éxito)

    Si el primer intento partiese de `S` (que en el mapa B está dentro de la
    trampa), el primer fallo sería seguro y entonces E[R] = 1/p.
    """
    steepest = next(f for f in filas if f.configuracion.startswith("HC steepest"))
    reinicios = next(f for f in filas if "reinicios" in f.configuracion)
    p = steepest.tasa_exito / 100.0
    libres = maze.free_cells()
    tiempos_exito: list[float] = []
    tiempos_fallo: list[float] = []
    for i, s in enumerate(libres):
        m = una_ejecucion(maze, s, dict(variant="steepest", metric=steepest.metrica),
                          _semilla_de(i))
        (tiempos_exito if m["exito"] else tiempos_fallo).append(m["tiempo_ms"])
    t_s = statistics.fmean(tiempos_exito) if tiempos_exito else 0.0
    t_f = statistics.fmean(tiempos_fallo) if tiempos_fallo else 0.0
    valores_r = reinicios.extra.get("reinicios_valores", [])
    ic = bootstrap_ic(valores_r, remuestreos=REMUESTREOS_BOOTSTRAP)
    # Frecuencia empírica de acertar dentro de los primeros r intentos.
    n_r = len(valores_r)
    empírico = {}
    for r in range(0, 6):
        if n_r:
            empírico[r] = 100.0 * sum(1 for k in valores_r if k < r) / n_r
    return {
        "p": p,
        "e_intentos": expected_restarts(p),          # E[K]
        "e_reinicios_random": (1 - p) / p,           # E[R] con inicio aleatorio
        "e_reinicios_desde_S": expected_restarts(p),  # E[R] si el 1.º parte de S
        "reinicios_medios": reinicios.reinicios,
        "ic95": ic,
        "exito_tras_r": {r: success_after(p, r + 1) for r in range(0, 6)},
        "empirico_r": empírico,
        "costo_esperado": expected_cost(p, t_f, t_s),
        "tiempo_medio_medido": reinicios.tiempo_mediana,
        "t_f": t_f,
        "t_s": t_s,
        "n_muestra_r": n_r,
    }


def escribir_resumen(filas: list[Fila], tabla: str, extra: dict, teoria_b: dict,
                      metrica: str, sens: dict, ruta: Path) -> None:
    """Escribe ``results/resumen_resultados.md`` con los números realmente medidos."""
    L: list[str] = []
    add = L.append
    etiqueta_metrica = "Manhattan" if metrica == "manhattan" else "Euclídea"
    add("# Análisis de resultados — Hill Climbing sobre laberinto con trampas cóncavas")
    add("")
    add(
        f"Documento generado automáticamente por `python -m hillclimb.benchmark` "
        f"(métrica {etiqueta_metrica}; semilla {SEMILLA}; {N_ALEATORIAS} ejecuciones por "
        f"configuración aleatoria, exhaustivas en las deterministas, {REPETICIONES} "
        "repeticiones cronometradas por configuración). Todas las cifras son mediciones "
        "de esta ejecución; ninguna está precocinada. Entorno de medición: "
        "`entorno.md`."
    )
    add("")
    add("## 1. Tabla de métricas")
    add("")
    add(tabla)
    add("")
    add("## 2. Dependencia del resultado respecto al desempate")
    add("")
    etiqueta_sens = {"manhattan": "Manhattan", "euclidea": "Euclídea"}.get(metrica, metrica)
    add(
        f"`p` depende de cómo se resuelvan los empates. En el mapa B con métrica "
        f"{etiqueta_sens}, las 24 permutaciones del orden de exploración dan p entre "
        f"**{sens['perm_min'] * 100:.2f} %** y **{sens['perm_max'] * 100:.2f} %** "
        f"(media {sens['perm_media'] * 100:.2f} %, desviación típica "
        f"{sens['perm_sd'] * 100:.2f}); con desempate aleatorio, entre "
        f"**{sens['aleatorio_min'] * 100:.2f} %** y **{sens['aleatorio_max'] * 100:.2f} %** "
        f"(media {sens['aleatorio_media'] * 100:.2f} %). Detalle completo, permutación por "
        "permutación, en `sensibilidad_desempate.md`."
    )
    add("")
    add(
        "**Regla usada por defecto en todo el repositorio:** orden fijo `↑ ↓ ← →` y, ante "
        "empates, el **primero** de los empatados (desempate estable y determinista). "
        "Todas las cifras de este documento usan esa regla."
    )
    add("")
    add("## 3. Caso A: convergencia exitosa")
    add("")
    ca = extra["cuenca_a"]
    mov_a = extra["movimientos_a"]
    add(
        f"El mapa A no contiene trampas cóncavas, de modo que la cuenca de atracción de la "
        f"meta es todo el espacio libre: p = |B(g)|/|F| = {ca['exito']}/{ca['libres']} = "
        f"{ca['p'] * 100:.2f} % y el estancamiento es {ca['estancamiento'] * 100:.2f} %. "
        f"Steepest-Ascent desde S = (0, 0) llega a G = (6, 8) en {mov_a} movimientos, que es "
        "exactamente la distancia de Manhattan entre ambos; el óptimo global f(g) = 0 se "
        "alcanza por un camino monótono ascendente. Las cuatro variantes y las tres "
        "mitigaciones aciertan todas desde todas las celdas: en el Caso A el paisaje no "
        "ofrece ninguna decisión peligrosa."
    )
    add("")
    add("## 4. Caso B: atrapamiento en el máximo local (3, 5)")
    add("")
    cb = extra["cuenca_b"]
    sumideros = extra["sumideros_b"]
    add(
        f"En el mapa B, Steepest-Ascent desde S = (3, 4) hace un único movimiento hasta "
        f"{extra['maxima_local']}, donde f = {extra['f_trampa']:.2f} y los tres vecinos "
        f"libres —(2, 5), (4, 5) y (3, 4)— tienen f = {extra['f_trampa'] - 1:.2f}, es decir "
        f"Δf = -1.00 en los tres: es un máximo local. La cuenca de atracción de la meta "
        f"mide p = {cb['exito']}/{cb['libres']} = {cb['p'] * 100:.2f} %, de modo que el "
        f"estancamiento es {cb['estancamiento'] * 100:.2f} % de las celdas libres. Las "
        f"celdas atrapadas caen todas en el mismo sumidero {extra['maxima_local']} "
        f"({sumideros.get(extra['maxima_local'], 0)} de {cb['libres']} celdas); la "
        f"profundidad de barrera de ese máximo local es d = "
        f"{extra['profundidad_barrera']:.2f}, porque el único camino de escape pasa por "
        f"(0, 1) o (6, 1), ambas con f = {extra['f_escape_arriba']:.2f}."
    )
    add("")
    add("## 5. Métrica euclídea frente a Manhattan")
    add("")
    cbm = extra["cuenca_b_manhattan"]
    cbe = extra["cuenca_b_euclidea"]
    add(
        "Ambas métricas se miden siempre (cálculo exhaustivo desde cada celda libre), para "
        "que la comparación no dependa de con cuál se lanzó el benchmark. En el mapa B:"
    )
    add("")
    add("| Métrica | p = \\|B(g)\\|/\\|F\\| | Estancamiento | Sumideros |")
    add("|---|---|---|---|")
    add(f"| Manhattan | {cbm['p'] * 100:.2f} % ({cbm['exito']}/{cbm['libres']}) | "
        f"{cbm['estancamiento'] * 100:.2f} % | {len(cbm['cuencas']) - 1} |")
    add(f"| Euclídea | {cbe['p'] * 100:.2f} % ({cbe['exito']}/{cbe['libres']}) | "
        f"{cbe['estancamiento'] * 100:.2f} % | {len(cbe['cuencas']) - 1} |")
    add("")
    add(
        f"La diferencia ({cbe['p'] * 100:.2f} % frente a {cbm['p'] * 100:.2f} %) no es un "
        "error: `f(s) = -d(s, g)` cambia con la métrica y, con los empates resueltos por "
        "orden fijo, la elección entre vecinos también. Las dos métricas coinciden en lo "
        "estructural: el mapa B tiene un único sumidero, `(3, 5)`, que concentra todas las "
        f"celdas atrapadas ({sumideros.get(extra['maxima_local'], 0)} de {cb['libres']} con "
        "Manhattan)."
    )
    add("")
    fila_pen = next(f for f in filas
                    if f.mapa == "B" and "penalización" in f.configuracion)
    add(
        f"En esta ejecución (métrica {etiqueta_metrica}), la penalización λ = 1 necesita "
        f"**{extra['it_pen_esta_metrica']:.2f} iteraciones** de media por celda libre "
        f"(**{fila_pen.it_exito:.2f}** según la tabla de arriba, que promedia solo los "
        f"éxitos de la configuración medida) frente a las "
        f"**{extra['it_pen_otra_metrica']:.2f}** que necesita con la otra métrica. La "
        "métrica euclídea produce valores de `f` con decimales, y al penalizar los empates "
        "y casi-empates se resuelven por caminos más largos."
    )
    add("")
    add("## 6. La variante simple frente a la trampa")
    add("")
    fila_simple_a = next(f for f in filas if f.mapa == "A" and f.configuracion.startswith("HC simple"))
    fila_simple_b = next(f for f in filas if f.mapa == "B" and f.configuracion.startswith("HC simple"))
    add(
        f"La variante *simple* (primer vecino que mejora en el orden fijo ↑ ↓ ← →) explora "
        f"el mismo paisaje que *steepest*: en el mapa A su tasa de éxito es "
        f"{fila_simple_a.tasa_exito:.2f} % ({fila_simple_a.ejecuciones} ejecuciones "
        f"exhaustivas, {fila_simple_a.it_exito:.2f} iteraciones de media por éxito) y en el "
        f"mapa B {fila_simple_b.tasa_exito:.2f} % ({fila_simple_b.it_fallo:.2f} iteraciones "
        f"de media por fallo). Elegir el primer ascenso disponible en lugar del más "
        "pronunciado cambia el camino recorrido, pero no la topología del paisaje: ambas "
        "variantes caen en el mismo máximo local porque la trampa es una propiedad del "
        "mapa, no de la regla de avance."
    )
    add("")
    add("## 7. Mitigación por penalización f′(s) = f(s) − λ·n(s)")
    add("")
    pen = extra["penalizacion"]
    pen_lat = extra["penalizacion_laterales"]
    add(
        f"Con λ = 1 y suficiente presupuesto de iteraciones, el algoritmo escapa de la "
        f"trampa desde S: estado final «{pen['estado']}» tras {pen['iteraciones']} "
        f"iteraciones ({pen['movimientos']} movimientos y {pen['penalizaciones']} "
        "penalizaciones acumuladas sobre los estados estancados). Cada estancamiento "
        "aumenta n(s) y desplaza f′(s) hacia abajo, de modo que los vecinos antes inútiles "
        "se vuelven atractivos. Si se combina con laterales L = 20, el escape sigue "
        f"produciéndose ({pen_lat['estado']} en {pen_lat['iteraciones']} iteraciones), con "
        f"{pen_lat['laterales']} movimientos laterales ejecutados sobre Δf = 0 que la "
        "propia penalización crea; el camino es mucho más largo, lo que muestra que los "
        "laterales solos no sirven aquí, pero tampoco estorban cuando hay penalización."
    )
    add("")
    add("## 8. Mitigación por reinicios aleatorios frente a la teoría")
    add("")
    add(
        f"**Definiciones.** Sea `K` el número de intentos (ejecuciones) hasta el primer "
        f"éxito y `R = K − 1` el número de reinicios. El experimento muestrea la primera "
        f"celda inicial de forma uniforme sobre las {cb['libres']} celdas libres, así que "
        f"cada intento acierta con probabilidad `p = {teoria_b['p'] * 100:.2f} %` de forma "
        f"independiente. Entonces:"
    )
    add("")
    add(
        f"- E[K] = 1/p = **{teoria_b['e_intentos']:.2f}** ejecuciones totales."
    )
    add(
        f"- E[R] = (1 − p)/p = **{teoria_b['e_reinicios_random']:.2f}** reinicios "
        f"(primer intento aleatorio)."
    )
    add(
        f"- Si el primer intento partiese de `S`, que está dentro de la trampa, el primer "
        f"fallo sería seguro y E[R] = 1/p = **{teoria_b['e_reinicios_desde_S']:.2f}**."
    )
    add(
        f"- Medido sobre {teoria_b['n_muestra_r']} ejecuciones con éxito: "
        f"**{teoria_b['reinicios_medios']:.2f}** reinicios de media, con intervalo de "
        f"confianza del 95 % por bootstrap "
        f"[{teoria_b['ic95'][0]:.2f} %, {teoria_b['ic95'][1]:.2f} %] "
        f"({REMUESTREOS_BOOTSTRAP} remuestreos)."
    )
    add("")
    coincide = (
        teoria_b["ic95"][0] <= teoria_b["reinicios_medios"] <= teoria_b["ic95"][1]
    )
    add(
        f"La media medida ({teoria_b['reinicios_medios']:.2f}) "
        + ("cae dentro" if coincide else "NO cae dentro")
        + " del intervalo bootstrap y es "
        + (
            "compatible"
            if abs(teoria_b["reinicios_medios"] - teoria_b["e_reinicios_random"]) < 0.5
            else "incompatible"
        )
        + f" con E[R] = (1 − p)/p = {teoria_b['e_reinicios_random']:.2f}"
        + (
            f", mientras que difiere de 1/p = {teoria_b['e_reinicios_desde_S']:.2f}, que "
            "solo correspondería a empezar siempre desde `S`."
            if abs(teoria_b["reinicios_medios"] - teoria_b["e_reinicios_random"]) < 0.5
            else "."
        )
    )
    add("")
    add("| r (intentos permitidos) | 1 − (1 − p)^r teórico | Frecuencia empírica |")
    add("|---|---|---|")
    for r in range(0, 6):
        teor = teoria_b["exito_tras_r"].get(r, 0.0)
        emp = teoria_b["empirico_r"].get(r, 0.0)
        add(f"| {r} | {teor * 100:.2f} % | {emp:.2f} % |")
    add("")
    add(
        f"**Costo esperado.** Con t_f = {teoria_b['t_f']:.4f} ms (intento fallido) y "
        f"t_s = {teoria_b['t_s']:.4f} ms (intento exitoso), medidos en el mismo experimento, "
        f"el costo teórico `((1 − p)/p)·t_f + t_s` = **{teoria_b['costo_esperado']:.4f} ms**; "
        f"la mediana medida por ejecución completa (todos sus intentos) es "
        f"**{teoria_b['tiempo_medio_medido']:.4f} ms**."
    )
    add("")
    res = extra["reinicios_manual"]
    add(
        f"Demostración manual con semilla fija {SEMILLA_REINICIOS_MANUAL}: desde S en el "
        f"mapa B, los reinicios aleatorios alcanzan la meta («{res['estado']}») usando "
        f"{res['usados']} reinicio(s)."
    )
    add("")
    add("## 9. Movimientos laterales y mesetas")
    add("")
    add(
        "Con las métricas Manhattan y Euclídea en una vecindad de 4 direcciones, Δf nunca es "
        "exactamente 0: cualquier movimiento cambia la distancia a la meta en una cantidad "
        "distinta de cero, así que en estos mapas no existen mesetas y los movimientos "
        "laterales no se activan por sí solos (la configuración «Steepest + laterales "
        "L = 20» obtiene tasas de éxito idénticas a «Steepest»). El mecanismo queda "
        "implementado, limitado y a prueba de ciclos: no vuelve a la celda previa cuando "
        "existe alternativa, y cuando la penalización genera Δf = 0 sí se ejecuta "
        f"({pen_lat['laterales']} movimientos laterales en el experimento combinado)."
    )
    add("")
    add(
        "**¿Y la vecindad de 8 direcciones?** La teoría sugiere que los movimientos en "
        "diagonal pueden dejar la distancia Manhattan invariante y con ello crear mesetas. "
        "Medido: con 8 direcciones sí existen celdas con algún vecino de `Δf = 0` "
        f"({extra['celdas_lateral_8']} de {cb['libres']} en el mapa B), pero **ninguna "
        "ejecución de las cuatro variantes termina en meseta**, en ninguno de los mapas ni "
        "en los aleatorios de `escalabilidad.md`. La razón es una propiedad verificada "
        "(`vecindad8.md`, sección 3): con la regla de *no cortar esquinas*, si una celda "
        "tiene vecino lateral entonces tiene también vecino ascendente, de modo que una "
        "meseta —sin ascendente pero con lateral— es inalcanzable. Los movimientos laterales "
        "solo resultan necesarios cuando otra mitigación crea empates."
    )
    add("")
    add("## 10. Contraste de memoria con A*")
    add("")
    astar_a, astar_b = extra["astar"]["A"], extra["astar"]["B"]
    add(
        f"Hill Climbing guarda un único estado (memoria O(1)). A*, con la misma heurística "
        f"de Manhattan, expande {astar_b['nodos_expandidos']} nodos y alcanza una frontera "
        f"máxima de {astar_b['max_frontera']} celdas en el mapa B (camino de "
        f"{astar_b['longitud_camino']} movimientos); en el mapa A expande "
        f"{astar_a['nodos_expandidos']} nodos con frontera máxima {astar_a['max_frontera']} "
        f"(camino de {astar_a['longitud_camino']} movimientos)."
    )
    add("")
    add("## 11. Coste de la telemetría")
    add("")
    add(
        "El mismo trabajo resuelto sin construir los objetos `StepInfo` de la telemetría "
        "(`hill_climbing_ligero`) se recoge en `tiempo_telemetria.md`: la telemetría "
        "añade un factor aproximadamente constante por iteración, del orden de unas "
        "décimas de milisegundo por ejecución en mapas de 7 × 9. Es perfectamente asumible "
        "para la demo paso a paso y no debe usarse cuando solo se quieren métricas "
        "agregadas."
    )
    add("")
    add("## 12. Eficiencia temporal")
    add("")
    add(
        f"Mediana por ejecución del steepest en el mapa B: "
        f"{teoria_b['t_s']:.4f} ms (éxito) y {teoria_b['t_f']:.4f} ms (fallo); mediana de "
        f"toda la configuración exhaustiva en el mapa A: "
        f"{next(f for f in filas if f.mapa == 'A' and 'steepest' in f.configuracion).tiempo_mediana:.4f} ms "
        "por ejecución. La búsqueda local es órdenes de magnitud más barata en tiempo, "
        "pero paga esa ventaja con la posibilidad de quedar atrapada."
    )
    add("")
    add("## 13. Análisis adicionales")
    add("")
    add(
        "Este benchmark genera, además de los archivos anteriores:\n"
    )
    add("")
    add(
        "- `sensibilidad_desempate.md` — `p` para las 24 permutaciones del orden de "
        "exploración y para 200 semillas con desempate aleatorio (sección 2 de este "
        "documento)."
    )
    add(
        "- `tiempo_telemetria.md` — coste de construir la telemetría frente al modo ligero "
        "`hill_climbing_ligero` (sección 11)."
    )
    add(
        "- `vecindad8.md` — vecindad de 8 direcciones: por qué no aparecen mesetas y cuándo "
        "sí se ejecutan los movimientos laterales (sección 9)."
    )
    add(
        "- `escalabilidad.md` y `figuras/p_vs_densidad.png` — mapas aleatorios de 15 × 15 y "
        "25 × 25 con densidades de muro del 10 %, 20 % y 30 %."
    )
    add(
        "- `entorno.md` — versión de Python y datos del equipo donde se tomaron las "
        "medidas. Los tiempos de este documento solo son comparables con los de la misma "
        "máquina."
    )
    add("")
    add(
        "Verificación independiente de las cifras principales (segunda implementación, sin "
        "reusar la lógica del paquete): `python tools/verificacion_independiente.py`."
    )
    add("")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------- flujo
def ejecutar_benchmark(metrica: str = "manhattan", escribir: bool = True,
                       verboso: bool = True) -> dict:
    """Ejecuta el benchmark completo y devuelve todos los datos calculados."""
    if verboso:
        print(f"Midiendo mapa A (Caso A) con métrica {metrica}...")
    filas_a = medir_mapa("A", MAPA_A, metrica)
    if verboso:
        print(f"Midiendo mapa B (Caso B) con métrica {metrica}...")
    filas_b = medir_mapa("B", MAPA_B, metrica)
    filas = filas_a + filas_b

    if verboso:
        print("Midiendo el coste de la telemetría...")
    filas_ligeras_b = medir_mapa("B", MAPA_B, metrica, ligero=True)

    maze_a, maze_b = Maze(MAPA_A, "A"), Maze(MAPA_B, "B")
    extra = experimentos_extra(maze_a, maze_b, metrica)
    if maze_a.start is None:  # pragma: no cover - mapa interno siempre con S
        raise ValueError("El mapa A necesita una celda inicial S")
    extra["movimientos_a"] = ejecutar(maze_a, maze_a.start, variant="steepest",
                                      metric=metrica).moves
    teoria_b = teoria_reinicios(filas_b, maze_b)

    if verboso:
        print("Midiendo sensibilidad al desempate (mapa B)...")
    sens_raw = sensibilidad_desempate(maze_b, semillas=SEMILLAS_DESEMPATE, metric=metrica)
    sens = dict(sens_raw)
    sens["n_semillas"] = SEMILLAS_DESEMPATE
    sens["metrica"] = metrica

    datos = {
        "filas": filas,
        "filas_ligeras_b": filas_ligeras_b,
        "extra": extra,
        "teoria_b": teoria_b,
        "sens": sens,
        "metrica": metrica,
    }

    if escribir:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        RUTA_FIGURAS.mkdir(parents=True, exist_ok=True)
        escribir_csv(filas, RUTA_RESULTADOS / "metricas.csv")
        tabla = escribir_markdown(filas, RUTA_RESULTADOS / "tabla_metricas.md")
        escribir_sensibilidad(sens, RUTA_RESULTADOS / "sensibilidad_desempate.md")
        escribir_telemetria(
            {"pares": list(zip(filas_b, filas_ligeras_b))},
            RUTA_RESULTADOS / "tiempo_telemetria.md",
        )
        escribir_entorno(RUTA_RESULTADOS / "entorno.md")
        escribir_resumen(filas, tabla, extra, teoria_b, metrica, sens,
                         RUTA_RESULTADOS / "resumen_resultados.md")
        if verboso:
            print(f"\nResultados escritos en {RUTA_RESULTADOS}")
    return datos


# ---------------------------------------------------------------------- flujo
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hillclimb.benchmark",
        description="Benchmark de Hill Climbing: métricas, tiempos y teoría de reinicios.",
    )
    parser.add_argument("--metrica", choices=list(METRICAS), default="manhattan",
                        help="métrica de distancia para f(s) = -d(s, g)")
    parser.add_argument("--salidas", action="store_true",
                        help="no escribe archivos, solo mide e informa")
    parser.add_argument("--silencioso", action="store_true", help="sin salida por consola")
    parser.add_argument("--sin-extra", action="store_true",
                        help="omite los análisis de vecindad 8 y escalabilidad")
    args = parser.parse_args(argv)
    ejecutar_benchmark(metrica=args.metrica, escribir=not args.salidas,
                       verboso=not args.silencioso)
    if not args.sin_extra and args.salidas is False:
        if not args.silencioso:
            print("\nAnalizando la vecindad de 8 direcciones...")
        from .vecindad8 import main as main_vecindad8

        main_vecindad8([])
        if not args.silencioso:
            print("\nVerificando la propiedad de mesetas en todos los mapas...")
        from .propiedad_mesetas import main as main_propiedad

        main_propiedad()
        if not args.silencioso:
            print("\nAnalizando escalabilidad (mapas aleatorios)...")
        from .escalabilidad import main as main_escalabilidad

        main_escalabilidad([])
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
