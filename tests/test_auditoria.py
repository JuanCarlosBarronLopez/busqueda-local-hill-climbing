"""Pruebas de la auditoría: robustez, reproducibilidad, casos borde y GUI."""

from __future__ import annotations

import random
import tkinter as tk
from pathlib import Path

import pytest

from hillclimb.algorithms import (
    hill_climbing,
    hill_climbing_ligero,
    random_restart,
)
from hillclimb.analysis import mesetas_posibles
from hillclimb.maze import MAPA_A, MAPA_B, Maze
from hillclimb.maze import MOVES, MOVES_8

RUTA_RAIZ = Path(__file__).resolve().parent.parent


def _pasos(maze: Maze, **kw):
    return list(hill_climbing(maze, maze.start, **kw))


# ============================================================ 1. Propiedad f creciente
@pytest.mark.parametrize("filas", [MAPA_A, MAPA_B])
@pytest.mark.parametrize(
    "variante", ["simple", "steepest", "stochastic", "first_choice"]
)
def test_f_estrictamente_creciente_sin_mitigacion(filas, variante) -> None:
    """Para TODAS las celdas: f crece en cada movimiento y no se repite celda."""
    maze = Maze(filas)
    for s in maze.free_cells():
        infos = list(
            hill_climbing(maze, s, variant=variante, rng=random.Random(11))
        )
        celdas = [i.current for i in infos]
        assert len(set(celdas)) == len(celdas), f"Ciclo desde {s} con {variante}"
        for a, b in zip(infos, infos[1:]):
            if a.current != b.current:
                assert b.f_current > a.f_current, (
                    f"f no creció de {a.current} a {b.current} desde {s}"
                )


# ============================================================ 2. Reproducibilidad
def test_misma_semilla_misma_trayectoria() -> None:
    """Misma semilla => trayectoria idéntica en las variantes aleatorias."""
    maze = Maze(MAPA_B)
    for variante in ("stochastic", "first_choice"):
        for inicio in maze.free_cells():
            trayectorias = []
            for _ in range(3):
                infos = list(
                    hill_climbing(maze, inicio, variant=variante, rng=random.Random(7))
                )
                trayectorias.append([(i.current, i.chosen) for i in infos])
            assert trayectorias[0] == trayectorias[1] == trayectorias[2]

    # Comprobación de que no es un falso positivo: en alguna celda con varias
    # rutas posibles, semillas distintas tienen que dar caminos distintos.
    caminos_distintos = set()
    for semilla in range(60):
        for inicio in ((0, 0), (0, 7), (6, 8), (2, 2)):
            infos = list(hill_climbing(
                maze, inicio, variant="stochastic", rng=random.Random(semilla)
            ))
            caminos_distintos.add(tuple((i.current, i.chosen) for i in infos))
    assert len(caminos_distintos) > 1, (
        "Todas las semillas dan el mismo camino: la semilla no está surtiendo efecto"
    )


def test_reinicios_reproducibles_con_semilla() -> None:
    """Los reinicios aleatorios con semilla fija repiten el resultado."""
    maze = Maze(MAPA_B)
    resultados = []
    for _ in range(3):
        ultimo = None
        for info in random_restart(maze, maze.start, random.Random(2024),
                                   max_restarts=50):
            ultimo = info
        resultados.append((ultimo.status, ultimo.restart, ultimo.iteration))
    assert resultados[0] == resultados[1] == resultados[2]


# ============================================================ 3. Consistencia de StepInfo
def test_consistencia_stepinfo() -> None:
    """Iteraciones de 1 en 1, movimientos coherentes y penalizaciones ≥ 0."""
    maze = Maze(MAPA_B)
    for kw in (
        dict(variant="steepest"),
        dict(variant="steepest", penalty_lambda=1.0, max_iter=2000),
        dict(variant="simple", penalty_lambda=0.5, max_iter=2000),
    ):
        infos = _pasos(maze, **kw)
        assert [i.iteration for i in infos] == list(range(1, len(infos) + 1)), kw
        # El contador de movimientos coincide con los pasos con elección.
        con_movimiento = [i for i in infos if i.chosen is not None]
        assert infos[-1].moves == len(con_movimiento), kw
        for i in infos:
            assert all(v >= 0 for v in i.penalties.values()), kw
            assert i.f_current <= 0.0 + 1e-9, kw
            assert i.stalls >= 0, kw


def test_consistencia_modo_ligero_vs_telemetria() -> None:
    """El modo ligero llega al mismo estado que el telemetrado."""
    maze = Maze(MAPA_B)
    for variante in ("simple", "steepest", "stochastic", "first_choice"):
        for kw in (dict(), dict(penalty_lambda=1.0), dict(sideways_limit=5)):
            referencia = hill_climbing(
                maze, maze.start, variant=variante, rng=random.Random(3),
                max_iter=3000, **kw,
            )
            ultimo = None
            for info in referencia:
                ultimo = info
            ligero = hill_climbing_ligero(
                maze, maze.start, variant=variante, rng=random.Random(3),
                max_iter=3000, **kw,
            )
            assert ligero["status"] == ultimo.status, (variante, kw)
            assert ligero["iteraciones"] == ultimo.iteration, (variante, kw)
            assert ligero["movimientos"] == ultimo.moves, (variante, kw)


# ============================================================ 4. Casos borde
def test_meta_encerrada_con_reinicios_termina() -> None:
    """Meta inalcanzable: los reinicios se agotan sin colgarse."""
    maze = Maze([
        "# S #",
        "# # #",
        "# . G",
    ], "inalcanzable")
    # S en (0,1) está aislada y G en (2,2) es inalcanzable desde ella.
    assert maze.neighbors((0, 1)) == []
    # Para que el resultado sea determinista, el generador solo puede proponer
    # celdas desde las que no se llega a G (nunca la propia G).
    class RngSinMeta(random.Random):
        """Generador whose `choice` nunca devuelve la celda meta."""

        def choice(self, seq):
            opciones = [c for c in seq if c != maze.goal] or list(seq)
            return opciones[0]

    infos = list(random_restart(maze, maze.start, RngSinMeta(1), max_restarts=5,
                                max_iter=20))
    assert infos[-1].status == "max_reinicios"
    assert infos[-1].restart == 5
    assert len(infos) <= 6 * 20 + 1  # acotado: no se cuelga


def test_s_igual_a_g() -> None:
    """S y G en la misma celda: éxito inmediato (estado artificial, el formato
    de texto no permite marcarlos a la vez en una celda)."""
    maze = Maze(["S G"], "s=g")
    maze.start = maze.goal  # se fuerza el estado inicial sobre la meta
    infos = _pasos(maze)
    assert len(infos) == 1
    assert infos[0].status == "goal"
    assert infos[0].f_current == 0.0
    assert infos[0].moves == 0


def test_s_en_bolsillo_cerrado() -> None:
    """S rodeada de muros: termina como máximo local sin fallar."""
    maze = Maze(["# S #", "# # #", "# . G"], "bolsillo")
    assert maze.start == (0, 1)
    assert maze.neighbors((0, 1)) == []
    infos = list(hill_climbing(maze, (0, 1)))
    assert infos[-1].status == "local_max"
    assert infos[-1].evaluations == []
    assert "aislada" in infos[-1].decision
    assert infos[-1].moves == 0


def test_mapa_1x2() -> None:
    """Mapa mínimo de una fila y dos columnas."""
    maze = Maze(["S G"], "1x2")
    assert maze.free_cells() == [(0, 0), (0, 1)]
    infos = _pasos(maze)
    assert infos[-1].status == "goal"
    assert infos[-1].moves == 1
    # Y al revés: desde G no hay nada que hacer más que declarar la meta.
    assert list(hill_climbing(maze, (0, 1)))[-1].status == "goal"


def test_max_iter_agotado() -> None:
    """Con penalización alta y max_iter pequeño se corta por el límite."""
    maze = Maze(MAPA_B)
    infos = list(hill_climbing(maze, maze.start, penalty_lambda=1.0, max_iter=3))
    assert infos[-1].iteration == 3
    assert infos[-1].status in ("max_iter", "running", "goal")


@pytest.mark.parametrize("lam", [0.01, 100.0])
def test_lambda_extremos(lam: float) -> None:
    """λ mínima y máxima: la ejecución termina siempre."""
    maze = Maze(MAPA_B)
    limite = 2000
    infos = _pasos(maze, penalty_lambda=lam, max_iter=limite)
    assert infos[-1].status in ("goal", "local_max", "plateau", "max_iter")
    # max_iter pasos «running» más el paso final que declara el límite.
    assert len(infos) <= limite + 1


@pytest.mark.parametrize("filas", [MAPA_A, MAPA_B])
def test_metrica_euclidea_termina(filas) -> None:
    """La métrica euclídea funciona en ambos mapas."""
    maze = Maze(filas)
    infos = _pasos(maze, metric="euclidea")
    assert infos[-1].status in ("goal", "local_max", "plateau")
    # f nunca es positiva.
    assert all(i.f_current <= 0.0 + 1e-9 for i in infos)


def test_vecindad_de_8_termina() -> None:
    """La vecindad de 8 direcciones acepta los 8 órdenes y no rompe nada."""
    assert len(MOVES) == 4 and len(MOVES_8) == 8
    maze = Maze(MAPA_B)
    for s in maze.free_cells():
        v8 = maze.neighbors(s, vecindad=8)
        assert len(v8) <= 8
        for _, t in v8:
            dr, dc = t[0] - s[0], t[1] - s[1]
            if dr != 0 and dc != 0:
                # No cortar esquinas: ambas ortogonales libres.
                assert maze.is_free((s[0] + dr, s[1]))
                assert maze.is_free((s[0], s[1] + dc))
    infos = _pasos(maze, vecindad=8)
    assert infos[-1].status in ("goal", "local_max", "plateau")


def test_vecindad_invalida_rechazada() -> None:
    """Una vecindad que no es 4 ni 8 debe fallar con un error claro."""
    maze = Maze(MAPA_A)
    with pytest.raises(ValueError):
        maze.neighbors((0, 0), vecindad=6)


# ============================================================ 5. Mesetas imposibles
@pytest.mark.parametrize("filas", [MAPA_A, MAPA_B])
@pytest.mark.parametrize("metrica", ["manhattan", "euclidea"])
def test_no_existen_mesetas_terminales(filas, metrica) -> None:
    """Ni con 4 ni con 8 direcciones: toda celda con lateral tiene ascendente."""
    maze = Maze(filas)
    prop = mesetas_posibles(maze, metrica)
    assert prop["solo_lateral"] == 0, (
        "Hay celdas con vecino lateral y sin ascendente: podrían ser mesetas"
    )
    assert prop["con_lateral"] == prop["con_lateral_y_ascendente"]
    # Y no hay ninguna ejecución que termine en meseta.
    for vecindad in (4, 8):
        for variante in ("simple", "steepest", "stochastic", "first_choice"):
            for s in maze.free_cells():
                infos = list(hill_climbing(
                    maze, s, variant=variante, rng=random.Random(2),
                    vecindad=vecindad, max_iter=3000,
                ))
                assert infos[-1].status != "plateau", (variante, vecindad, s)


# ============================================================ 6. GUI
def test_gui_no_se_rompe_con_ninguna_combinacion(tmp_path) -> None:
    """Paso, Auto, Ejecutar hasta el final, Reiniciar y Exportar no fallan.

    Si en el entorno no hay una instalación usable de Tk (sin pantalla o sin
    `init.tcl`), la prueba se omite en lugar de fallar: la GUI es una parte
    opcional del entregable y su verificación automática depende del sistema.
    """
    from hillclimb.gui import Aplicacion

    try:
        raiz = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"Tk no está disponible en este entorno: {exc}")
    raiz.withdraw()
    app = Aplicacion(raiz)
    destino = tmp_path / "_test_gui.png"
    combinaciones = 0
    for nombre_mapa in ("A (sin trampas)", "B (trampa en U)"):
        for variante in ("simple", "steepest", "stochastic", "first_choice"):
            for mitig in ("Ninguna", "Laterales (L)", "Penalización (λ)",
                          "Reinicios aleatorios"):
                for vecindad in ("4", "8"):
                    combinaciones += 1
                    app.var_mapa.set(nombre_mapa)
                    app.var_variante.set(variante)
                    app.var_mitigacion.set(mitig)
                    app.var_vecindad.set(vecindad)
                    app.var_param.set("20")
                    app._reiniciar()
                    for _ in range(5):  # Paso cinco veces
                        app.paso()
                    app.alternar_auto()  # Auto/Pausa
                    app.auto_stop()
                    app.ejecutar_final()
                    app.exportar_png(destino)
                    app._reiniciar()
    assert combinaciones >= 32
    assert destino.exists()

    # Mapa editado sin S o sin G: mensaje amigable, nunca traceback.
    app.maze.grid[3][4] = "."
    app.maze.start = None
    app._reiniciar()
    assert "Mapa incompleto" in app.var_estado_banner.get()
    app.paso()  # no debe lanzar
    app.ejecutar_final()
    app.exportar_png(destino)  # no debe lanzar
    app.guardar_registro()
    raiz.destroy()
