"""Exportación de figuras PNG con Pillow (no abre la GUI).

El mismo renderizador sirve para las figuras del reporte y para el botón
«Exportar PNG» de la interfaz: recibe el laberinto más lo que se quiera
resaltar (rastro del camino, estado actual, vecinos evaluados, cuencas de
atracción y etiquetas) y devuelve una imagen :class:`PIL.Image.Image`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .algorithms import Evaluation
from .maze import Cell, Maze

#: Tamaño de celda en píxeles.
CELDA = 64
MARGEN = 24
ALTO_CABECERA = 96
ALTO_PIE = 34

# Paleta (RGB)
FONDO = (247, 248, 250)
MURO = (44, 47, 51)
LINEA = (120, 126, 134)
CALOR_CERCANO = (222, 240, 250)  # celda cercana a la meta: más clara
CALOR_LEJANO = (108, 141, 168)  # celda lejana: más oscura
INICIO = (46, 125, 50)
META = (245, 176, 0)
ACTUAL = (230, 81, 0)
ELEGIDO = (21, 101, 192)
POSITIVO = (27, 94, 32)
NEGATIVO = (183, 28, 28)
CERO = (120, 120, 120)
TENUE = (176, 190, 202)
CUENCA_META = (200, 230, 201)
CUENCA_TRAMPA = (250, 205, 205)
TEXTO = (33, 37, 41)

#: Equivalentes ASCII por si la fuente disponible no tiene glifos de flecha.
ASCII = {"↑": "^", "↓": "v", "←": "<", "→": ">"}

Rastro = list[tuple[str, Cell]]


Color = tuple[int, int, int]


def _mezcla(a: Color, b: Color, t: float) -> Color:
    """Interpolación lineal entre dos colores."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _fuente(tamano: int, negrita: bool = False) -> tuple[ImageFont.ImageFont, bool]:
    """Carga una fuente TrueType si existe; si no, la fuente por defecto."""
    nombres = ("arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf") if negrita else (
        "arial.ttf", "seguisym.ttf", "DejaVuSans.ttf", "calibri.ttf",
    )
    for nombre in nombres:
        try:
            return ImageFont.truetype(nombre, tamano), True
        except OSError:
            continue
    return ImageFont.load_default(), False


def flecha(flecha: str, unicode_ok: bool) -> str:
    """Glifo de la flecha, en ASCII si la fuente no soporta Unicode."""
    return flecha if unicode_ok else ASCII.get(flecha, flecha)


def color_calor(maze: Maze, metric: str) -> dict[Cell, tuple[int, int, int]]:
    """Mapa de calor de ``f``: más claro cuanto más cerca de la meta."""
    libres = maze.free_cells()
    if not libres:
        return {}
    h_max = max(maze.h(c, metric) for c in libres) or 1.0
    return {
        c: _mezcla(CALOR_CERCANO, CALOR_LEJANO, maze.h(c, metric) / h_max)
        for c in libres
    }


def render(
    maze: Maze,
    titulo: str,
    subtitulo: str = "",
    *,
    rastro: Rastro | None = None,
    rastro_tenue: Rastro | None = None,
    actual: Cell | None = None,
    evaluaciones: Iterable[Evaluation] | None = None,
    elegido: Cell | None = None,
    cuencas: dict[Cell, list[Cell]] | None = None,
    marcas: dict[Cell, str] | None = None,
    metric: str = "manhattan",
    pie: str = "",
    tam_celda: int = CELDA,
) -> Image.Image:
    """Dibuja el laberinto con todo lo que se le indique y devuelve la imagen."""
    ancho = 2 * MARGEN + maze.C * tam_celda
    alto = ALTO_CABECERA + 2 * MARGEN + maze.R * tam_celda + ALTO_PIE
    img = Image.new("RGB", (ancho, alto), FONDO)
    d = ImageDraw.Draw(img)
    f_titulo, u1 = _fuente(22, negrita=True)
    f_sub, u2 = _fuente(14)
    f_celda, u3 = _fuente(15)
    f_flecha, u3b = _fuente(20, negrita=True)
    f_delta, u4 = _fuente(12, negrita=True)
    f_marca, u5 = _fuente(12, negrita=True)
    f_pie, u6 = _fuente(13)
    unicode_ok = all((u1, u2, u3, u3b, u4, u5, u6))

    ox, oy = MARGEN, ALTO_CABECERA
    calor = color_calor(maze, metric)
    tinte_cuenca: dict[Cell, tuple[int, int, int]] = {}
    if cuencas:
        for celda_destino, celdas_origen in cuencas.items():
            tinte = CUENCA_META if celda_destino == maze.goal else CUENCA_TRAMPA
            for origen in celdas_origen:
                tinte_cuenca[origen] = tinte

    # --- celdas ---------------------------------------------------------------
    for r in range(maze.R):
        for c in range(maze.C):
            x0, y0 = ox + c * tam_celda, oy + r * tam_celda
            x1, y1 = x0 + tam_celda, y0 + tam_celda
            celda = (r, c)
            if maze.grid[r][c] == "#":
                d.rectangle([x0, y0, x1, y1], fill=MURO, outline=MURO)
                continue
            color = calor.get(celda, FONDO)
            if celda in tinte_cuenca:
                color = _mezcla(color, tinte_cuenca[celda], 0.55)
            d.rectangle([x0, y0, x1, y1], fill=color, outline=LINEA)

    # --- rastro tenue (intentos fallidos de reinicios) ------------------------
    for arrow, celda in rastro_tenue or []:
        r, c = celda
        cx, cy = ox + c * tam_celda + tam_celda // 2, oy + r * tam_celda + tam_celda // 2
        d.text((cx, cy), flecha(arrow, unicode_ok), font=f_flecha, fill=TENUE, anchor="mm")

    # --- rastro principal ------------------------------------------------------
    for arrow, celda in rastro or []:
        r, c = celda
        cx = ox + c * tam_celda + tam_celda // 2
        # Si la celda lleva una etiqueta, la flecha se sube para no solaparse.
        cy = oy + r * tam_celda + tam_celda // 2 - (9 if celda in (marcas or {}) else 0)
        d.text((cx, cy), flecha(arrow, unicode_ok), font=f_flecha, fill=ELEGIDO, anchor="mm")

    # --- etiquetas Δf de los vecinos evaluados ---------------------------------
    for e in evaluaciones or []:
        r, c = e.cell
        x0, y0 = ox + c * tam_celda, oy + r * tam_celda
        color = POSITIVO if e.delta > 0 else (NEGATIVO if e.delta < 0 else CERO)
        d.text((x0 + tam_celda / 2, y0 + 6), f"Δ{e.delta:+.2f}", font=f_delta,
               fill=color, anchor="ma")
        d.rectangle([x0 + 1, y0 + 1, x0 + tam_celda - 1, y0 + tam_celda - 1],
                    outline=color, width=2)

    # --- S y G ------------------------------------------------------------------
    if maze.start:
        r, c = maze.start
        cx, cy = ox + c * tam_celda + tam_celda // 2, oy + r * tam_celda + tam_celda // 2
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=INICIO, outline=(255, 255, 255), width=2)
        d.text((cx, cy), "S", font=f_celda, fill=(255, 255, 255), anchor="mm")
    if maze.goal:
        r, c = maze.goal
        cx, cy = ox + c * tam_celda + tam_celda // 2, oy + r * tam_celda + tam_celda // 2
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=META, outline=(255, 255, 255), width=2)
        d.text((cx, cy), "G", font=f_celda, fill=(30, 30, 30), anchor="mm")

    # --- estado actual y elegido ------------------------------------------------
    if actual:
        r, c = actual
        d.rectangle(
            [ox + c * tam_celda + 2, oy + r * tam_celda + 2,
             ox + (c + 1) * tam_celda - 2, oy + (r + 1) * tam_celda - 2],
            outline=ACTUAL, width=4,
        )
    if elegido:
        r, c = elegido
        d.rectangle(
            [ox + c * tam_celda + 3, oy + r * tam_celda + 3,
             ox + (c + 1) * tam_celda - 3, oy + (r + 1) * tam_celda - 3],
            outline=ELEGIDO, width=4,
        )

    # --- marcas de texto sobre celdas -------------------------------------------
    for celda, texto in (marcas or {}).items():
        r, c = celda
        cx = ox + c * tam_celda + tam_celda // 2
        cy = oy + r * tam_celda + tam_celda - 11  # pegada al borde inferior
        ancho_txt = d.textlength(texto, font=f_marca)
        d.rectangle(
            [cx - ancho_txt / 2 - 5, cy - 9, cx + ancho_txt / 2 + 5, cy + 9],
            fill=NEGATIVO,
        )
        d.text((cx, cy), texto, font=f_marca, fill=(255, 255, 255), anchor="mm")

    # --- cabecera y pie -----------------------------------------------------------
    d.text((MARGEN, 28), titulo, font=f_titulo, fill=TEXTO)
    d.text((MARGEN, 60), subtitulo, font=f_sub, fill=(70, 76, 84))
    if pie:
        d.text((MARGEN, alto - ALTO_PIE + 8), pie, font=f_pie, fill=(70, 76, 84))
    return img


def camino(infos: Iterable) -> Rastro:
    """Reconstruye el rastro ``(flecha, celda)`` a partir de la telemetría."""
    rastro: Rastro = []
    for info in infos:
        if info.chosen is None:
            continue
        for e in info.evaluations:
            if e.cell == info.chosen:
                rastro.append((e.arrow, e.cell))
                break
    return rastro


def guardar(img: Image.Image, ruta: Path) -> Path:
    """Guarda la imagen como PNG creando las carpetas necesarias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img.save(ruta, "PNG")
    return ruta
