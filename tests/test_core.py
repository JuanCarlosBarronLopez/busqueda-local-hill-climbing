"""Pruebas del núcleo: mapa A (éxito), mapa B (trampa) y mitigaciones."""

from __future__ import annotations

import math
import random

from hillclimb.analysis import (
    barrier_depth,
    basin_of_attraction,
    basin_stats,
    expected_cost,
    expected_restarts,
    success_after,
)
from hillclimb.algorithms import (
    ETIQUETAS,
    StepInfo,
    ejecutar,
    hill_climbing,
    random_restart,
)
from hillclimb.maze import MAPA_A, MAPA_B, Maze


def _recorrido(maze: Maze, **kw) -> list[StepInfo]:
    """Consume el generador y devuelve todas las iteraciones."""
    return list(hill_climbing(maze, maze.start, **kw))


def test_mapa_a_llega_a_la_meta_en_14_movimientos() -> None:
    """Caso A: Steepest con orden ↑↓←→ llega a G desde S en 14 movimientos."""
    pasos = _recorrido(Maze(MAPA_A, "A"), variant="steepest")
    final = pasos[-1]
    assert final.status == "goal"
    assert final.current == (6, 8)
    assert final.moves == 14
    assert final.f_current == 0.0
    # Cada iteración intermedia eligió exactamente un vecino ascendente.
    for info in pasos[:-1]:
        assert info.chosen is not None
        assert info.status == "running"


def test_mapa_a_exito_desde_cualquier_celda_libre() -> None:
    """Caso A: 100 % de éxito (no existe ningún máximo local)."""
    maze = Maze(MAPA_A, "A")
    for celda in maze.free_cells():
        info = ejecutar(maze, celda, variant="steepest")
        assert info.status == "goal", f"Fallo desde {celda}: {info.status}"
    stats = basin_stats(Maze(MAPA_A, "A"))
    assert stats["p"] == 1.0
    assert stats["estancamiento"] == 0.0
    assert stats["libres"] == 58


def test_mapa_b_maximo_local_en_3_5() -> None:
    """Caso B: Steepest desde S se detiene en (3,5) con sus 3 vecinos en Δf = -1."""
    pasos = _recorrido(Maze(MAPA_B, "B"), variant="steepest")
    assert pasos[-1].status == "local_max"
    final = pasos[-1]
    assert final.current == (3, 5)
    assert final.f_current == -3.0
    assert final.chosen is None
    vecinos = {(e.arrow, e.cell): e for e in final.evaluations}
    assert set(vecinos) == {("↑", (2, 5)), ("↓", (4, 5)), ("←", (3, 4))}
    for e in final.evaluations:
        assert e.f == -4.0
        assert e.delta == -1.0
    assert "Máximo local" in final.decision
    # El camino recorrido fue (3,4) -> (3,5): un solo movimiento.
    assert final.moves == 1
    # Iteración 1: estado (3,4) y elección (3,5). Iteración 2: estado (3,5) y parada.
    assert [p.current for p in pasos] == [(3, 4), (3, 5)]


def test_profundidad_de_barrera_del_caso_b() -> None:
    """La barrera de (3,5) mide 7.0 (escapar pasa por (0,1) o (6,1), f = -10)."""
    maze = Maze(MAPA_B, "B")
    assert barrier_depth(maze, (3, 5)) == 7.0
    assert maze.f((0, 1)) == -10.0
    assert maze.f((6, 1)) == -10.0
    # Un máximo local de la cuenca contraria a la meta NO aparece en B(g).
    cuencas = basin_of_attraction(maze)
    assert (3, 5) in cuencas
    assert maze.goal not in cuencas[(3, 5)]


def test_penalizacion_escapa_de_la_trampa() -> None:
    """Caso B con λ = 1: la penalización por estancamiento escapa y llega a G."""
    maze = Maze(MAPA_B, "B")
    info = ejecutar(
        maze, (3, 4), variant="steepest",
        penalty_lambda=1.0, max_iter=5000,
    )
    assert info.status == "goal", f"La penalización no escapó (status={info.status})"
    # Se registra el número de iteraciones empleadas (dato para el reporte).
    print(f"\n[penalizacion lambda=1] iteraciones = {info.iteration}, movimientos = {info.moves}, "
          f"penalizaciones = {sum(info.penalties.values())}")
    assert info.iteration > 1


def test_reinicios_aleatorios_con_semilla_llegan_a_la_meta() -> None:
    """Caso B con reinicios aleatorios y semilla fija: se alcanza la meta."""
    maze = Maze(MAPA_B, "B")
    ultimo: StepInfo | None = None
    for info in random_restart(maze, maze.start, random.Random(2024), max_restarts=100):
        ultimo = info
    assert ultimo is not None
    assert ultimo.status == "goal"
    assert ultimo.restart >= 1  # el primer intento desde S queda atrapado
    print(f"\n[reinicios] reinicios usados = {ultimo.restart}, iteraciones = {ultimo.iteration}")


def test_sin_mitigacion_la_sucesion_es_estrictamente_creciente() -> None:
    """Sin mitigación: f crece en cada movimiento y ninguna celda se repite."""
    for filas in (MAPA_A, MAPA_B):
        maze = Maze(filas)
        for variante in ("simple", "steepest", "stochastic", "first_choice"):
            infos = list(
                hill_climbing(maze, maze.start, variant=variante, rng=random.Random(7))
            )
            celdas = [i.current for i in infos]
            assert len(set(celdas)) == len(celdas), f"Ciclo en {variante} sobre {filas}"
            for anterior, siguiente in zip(infos, infos[1:]):
                if anterior.current != siguiente.current:
                    assert siguiente.f_current > anterior.f_current, (
                        f"{variante}: f no creció de {anterior.current} a {siguiente.current}"
                    )


def test_celda_inicial_es_la_meta() -> None:
    """Caso borde: empezar en la meta termina de inmediato con f = 0."""
    maze = Maze(MAPA_A, "A")
    infos = list(hill_climbing(maze, maze.goal, variant="steepest"))
    assert len(infos) == 1
    assert infos[0].status == "goal"
    assert infos[0].moves == 0
    assert infos[0].evaluations == []


def test_celda_aislada_por_muros() -> None:
    """Caso borde: una celda rodeada de muros termina sin fallar."""
    maze = Maze(["S #", "# G"], "Aislada")
    assert maze.free_cells() == [(0, 0), (1, 1)]
    info = ejecutar(maze, (0, 0), variant="steepest")
    assert info.status in ("local_max", "plateau")
    assert info.evaluations == []
    assert info.f_current == -2.0
    # Y desde la meta, el mismo laberinto devuelve éxito inmediato.
    assert ejecutar(maze, (1, 1), variant="steepest").status == "goal"


def test_metrica_euclidea_y_desempate() -> None:
    """La métrica euclídea cambia f; el desempate sigue el orden fijo."""
    maze = Maze(MAPA_A, "A")
    info = ejecutar(maze, (0, 0), variant="steepest", metric="euclidea")
    assert info.status == "goal"
    assert math.isclose(info.f_current, 0.0)
    # Con Manhattan, desde (0,0) hay empate: ↓ (1,0) y → (0,1) tienen Δf = +1.00;
    # el desempate estable por orden fijo ↑ ↓ ← → elige ↓ (1,0).
    pasos = list(hill_climbing(maze, (0, 0), variant="steepest"))
    assert pasos[0].chosen == (1, 0)
    mejores = [e for e in pasos[0].evaluations if e.delta > 0]
    assert {e.cell for e in mejores} == {(1, 0), (0, 1)}
    assert all(e.delta == 1.0 for e in mejores)
    assert pasos[0].evaluations[0].arrow == "↓"  # orden fijo ↑ ↓ ← →


def test_fórmulas_teóricas_de_reinicios() -> None:
    """Reinicios esperados, éxito tras r reinicios y costo esperado."""
    p = 0.54
    assert math.isclose(expected_restarts(p), 1 / p)
    assert math.isclose(success_after(p, 3), 1 - (1 - p) ** 3)
    assert math.isclose(expected_cost(p, 10.0, 4.0), ((1 - p) / p) * 10.0 + 4.0)
    assert expected_restarts(0.0) == math.inf
    assert math.isclose(success_after(1.0, 0), 0.0)


def test_edicion_del_laberinto() -> None:
    """La GUI edita el mapa: alternar muros y mover S sin tocar G."""
    maze = Maze(MAPA_B, "Personalizado")
    assert maze.toggle_wall((3, 4)) is False  # no se puede murar S
    assert maze.toggle_wall((3, 8)) is False  # ni G
    assert maze.toggle_wall((0, 3)) is True  # libre -> muro
    assert maze.grid[0][3] == "#"
    assert maze.toggle_wall((0, 3)) is True  # muro -> libre
    assert maze.grid[0][3] == "."
    assert maze.toggle_wall((3, 6)) is True  # muro existente -> se puede quitar
    assert maze.grid[3][6] == "."
    assert maze.toggle_wall((9, 9)) is False  # fuera del tablero
    assert maze.set_start((6, 3)) is True
    assert maze.start == (6, 3)
    assert maze.grid[6][3] == "S"
    assert maze.grid[3][4] == "."
    assert maze.set_start((3, 8)) is False  # no sobre la meta
    assert len(maze.to_rows()) == maze.R


def test_etiquetas_de_estado_en_español() -> None:
    """Los estados terminales tienen etiqueta legible en español."""
    assert ETIQUETAS["local_max"] == "ATRAPADO EN MÁXIMO LOCAL"


def test_formato_de_telemetria_compartido() -> None:
    """La CLI y la GUI comparten el formato de telemetría."""
    from hillclimb.cli import formatear_paso

    pasos = _recorrido(Maze(MAPA_B, "B"), variant="steepest")
    texto = formatear_paso(pasos[-1])
    assert "Iteración 2 | Estado: (3, 5) | f = -3.00" in texto
    assert "↑ (2, 5)  f = -4.00  Δf = -1.00" in texto
    assert "Decisión: Máximo local" in texto
    assert "Resultado: ATRAPADO EN MÁXIMO LOCAL" in texto
    assert "Reinicio" not in texto


def test_laterales_se_activan_con_penalizacion() -> None:
    """Los movimientos laterales solo aparecen cuando algo crea Δf = 0."""
    maze = Maze(MAPA_B, "B")
    decisiones = [
        info.decision
        for info in hill_climbing(
            maze, (3, 4), variant="steepest",
            penalty_lambda=1.0, sideways_limit=20, max_iter=5000,
        )
    ]
    laterales = [d for d in decisiones if d.startswith("Movimiento lateral")]
    assert laterales, "Se esperaban movimientos laterales con λ=1 y L=20"
    assert laterales[0].startswith("Movimiento lateral 1/20")
    # Sin penalización no hay ningún movimiento lateral en estos mapas.
    sin_pen = [i.decision for i in hill_climbing(maze, (3, 4), variant="steepest", sideways_limit=20)]
    assert not any(d.startswith("Movimiento lateral") for d in sin_pen)


def test_limite_de_iteraciones() -> None:
    """Con penalización y max_iter pequeño se corta sin fallar."""
    maze = Maze(MAPA_B, "B")
    info = ejecutar(maze, (3, 4), variant="steepest", penalty_lambda=1.0, max_iter=5)
    assert info.status in ("max_iter", "running")
    assert info.iteration <= 5


def test_cli_en_modo_automatico() -> None:
    """La CLI corre sin pausas y termina con código 0."""
    from hillclimb.cli import main

    assert main(["--mapa", "B", "--variante", "steepest", "--auto"]) == 0
    assert main(["--mapa", "A", "--variante", "simple", "--auto"]) == 0
