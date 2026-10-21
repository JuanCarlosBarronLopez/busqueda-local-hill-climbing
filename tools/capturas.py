"""Toma capturas de cada parte del sistema, las analiza y publica las validas.

Genera imagenes de la GUI (varios escenarios), de la CLI y de los informes,
comprueba automaticamente que cada captura tiene contenido real (no esta en
blanco ni a medias) y solo copia a ``docs/imagenes/`` las que pasan el control.

Uso::

    python tools/capturas.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from PIL import Image, ImageDraw, ImageFont, ImageGrab  # noqa: E402

TEMPORAL = RAIZ / "results" / "_capturas"
DESTINO = RAIZ / "docs" / "imagenes"

# Colores que deben aparecer en una captura valida de la GUI.
CLAVES = {
    "inicio_S": (46, 125, 50),
    "meta_G": (245, 176, 0),
    "estado_actual": (230, 81, 0),
    "elegido_o_rastro": (21, 101, 192),
}


# ------------------------------------------------------------------ análisis
def analizar_banner(ruta: Path, esperado: str) -> bool:
    """Comprueba el color del banner de estado (esquina superior derecha).

    ``verde`` = exito alcanzado, ``rojo`` = estancamiento. Es la verificacion
    de que la captura muestra el escenario que dice mostrar.
    """
    if not ruta.exists() or esperado is None:
        return True
    imagen = Image.open(ruta).convert("RGB")
    ancho = imagen.width
    pixeles = imagen.load()
    objetivo = {"verde": (200, 230, 201), "rojo": (255, 205, 210)}.get(esperado)
    if objetivo is None:
        return True
    # El banner ocupa la parte alta del panel derecho, justo debajo de la
    # barra de controles (su altura varia segun el sistema).
    for y in range(90, 320, 2):
        for x in range(ancho - 470, ancho - 5, 3):
            if all(abs(pixeles[x, y][i] - objetivo[i]) <= 12 for i in range(3)):
                return True
    return False


def analizar(ruta: Path, exigir: tuple[str, ...] = (),
             banner: str | None = None) -> dict:
    """Comprueba que una captura tiene contenido real y los colores esperados."""
    if not ruta.exists():
        return {"ok": False, "motivo": "el archivo no existe"}
    imagen = Image.open(ruta).convert("RGB")
    if imagen.width < 400 or imagen.height < 300:
        return {"ok": False, "motivo": f"demasiado pequeña ({imagen.width}x{imagen.height})"}
    pixeles = imagen.load()
    distintos: set[tuple[int, int, int]] = set()
    for y in range(0, imagen.height, 6):
        for x in range(0, imagen.width, 6):
            distintos.add(pixeles[x, y])
    if len(distintos) < 40:
        return {"ok": False, "motivo": f"imagen casi uniforme ({len(distintos)} colores)"}
    presentes, ausentes = [], []
    if exigir:
        for nombre in exigir:
            objetivo = CLAVES[nombre]
            encontrado = any(
                all(abs(pixeles[x, y][i] - objetivo[i]) <= 28 for i in range(3))
                for y in range(0, imagen.height, 4)
                for x in range(0, imagen.width, 4)
            )
            (presentes if encontrado else ausentes).append(nombre)
        if ausentes:
            return {
                "ok": False,
                "motivo": f"faltan elementos: {', '.join(ausentes)}",
                "presentes": presentes,
            }
    return {
        "ok": True,
        "motivo": f"{imagen.width}x{imagen.height}, {len(distintos)} colores",
        "presentes": presentes,
    }


# ------------------------------------------------------------------ capturas GUI
def capturar_ventana(app, ruta: Path) -> Path:
    """Captura la ventana de la aplicacion y la guarda.

    Fuerza la ventana al frente antes de capturar: si otra ventana la tapa,
    ImageGrab captura lo que se ve en pantalla y la captura sale incompleta.
    """
    raiz = app.root
    raiz.update()
    raiz.lift()
    raiz.focus_force()
    raiz.attributes("-topmost", True)
    raiz.update()
    time.sleep(0.35)
    raiz.update()
    x, y = raiz.winfo_rootx(), raiz.winfo_rooty()
    ancho, alto = raiz.winfo_width(), raiz.winfo_height()
    imagen = ImageGrab.grab(bbox=(x, y, x + ancho, y + alto))
    raiz.attributes("-topmost", False)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(ruta)
    return ruta


def escenarios() -> list[tuple[str, dict]]:
    """Escenarios de la GUI a capturar, con los colores que deben aparecer."""
    return [
        (
            "01_caso_a_exito",
            {
                "mapa": "A (sin trampas)", "variante": "steepest", "metrica": "Manhattan",
                "vecindad": "4", "desempate": "fijo", "mitigacion": "Ninguna",
                "pasos": None,
                "exigir": ("inicio_S", "meta_G", "estado_actual", "elegido_o_rastro"),
                "banner": "verde",
            },
        ),
        (
            "02_caso_b_atrapado",
            {
                "mapa": "B (trampa en U)", "variante": "steepest", "metrica": "Manhattan",
                "vecindad": "4", "desempate": "fijo", "mitigacion": "Ninguna",
                "pasos": 2,
                "exigir": ("inicio_S", "meta_G", "estado_actual", "elegido_o_rastro"),
                "banner": "rojo",
            },
        ),
        (
            "03_penalizacion_escapa",
            {
                "mapa": "B (trampa en U)", "variante": "steepest", "metrica": "Manhattan",
                "vecindad": "4", "desempate": "fijo", "mitigacion": "Penalización (λ)",
                "param": "1.0", "pasos": None,
                "exigir": ("inicio_S", "meta_G", "estado_actual", "elegido_o_rastro"),
                "banner": "verde",
            },
        ),
        (
            "04_reinicios_aleatorios",
            {
                "mapa": "B (trampa en U)", "variante": "steepest", "metrica": "Manhattan",
                "vecindad": "4", "desempate": "fijo", "mitigacion": "Reinicios aleatorios",
                "param": "100", "semilla": "2024", "pasos": None,
                "exigir": ("inicio_S", "meta_G", "estado_actual", "elegido_o_rastro"),
                "banner": "verde",
            },
        ),
        (
            "05_vecindad8_mapa_calor",
            {
                "mapa": "B (trampa en U)", "variante": "steepest", "metrica": "Euclídea",
                "vecindad": "8", "desempate": "fijo", "mitigacion": "Ninguna",
                "pasos": 3,
                "exigir": ("inicio_S", "meta_G", "estado_actual"),
            },
        ),
    ]


def aplicar(app, cfg: dict) -> None:
    """Configura la aplicacion segun un escenario y ejecuta los pasos indicados."""
    app.var_mapa.set(cfg["mapa"])
    app.var_variante.set(cfg["variante"])
    app.var_metrica.set(cfg["metrica"])
    app.var_vecindad.set(cfg["vecindad"])
    app.var_desempate.set(cfg["desempate"])
    app.var_mitigacion.set(cfg["mitigacion"])
    if cfg.get("param"):
        app.var_param.set(cfg["param"])
    if cfg.get("semilla"):
        app.var_semilla.set(cfg["semilla"])
    app._reiniciar()
    if cfg["pasos"] is None:
        app.ejecutar_final()
    else:
        for _ in range(cfg["pasos"]):
            app.paso()


def capturas_gui() -> list[dict]:
    """Abre la GUI una vez y toma una captura por escenario."""
    import tkinter as tk

    from hillclimb.gui import Aplicacion

    raiz = tk.Tk()
    raiz.geometry("1240x800+40+30")
    app = Aplicacion(raiz)
    raiz.update()
    resultados = []
    for nombre, cfg in escenarios():
        try:
            aplicar(app, cfg)
            ruta = capturar_ventana(app, TEMPORAL / f"{nombre}.png")
            # Recorte del panel de telemetria para el escenario de atasco.
            if nombre == "02_caso_b_atrapado":
                imagen = Image.open(ruta)
                ancho, alto = imagen.size
                recorte = imagen.crop((ancho - 470, 40, ancho, alto - 20))
                ruta_recorte = TEMPORAL / "02b_telemetria_detalle.png"
                recorte.save(ruta_recorte)
            resultados.append({"nombre": nombre, "ruta": ruta, "cfg": cfg})
        except Exception as exc:  # noqa: BLE001
            resultados.append({"nombre": nombre, "ruta": None, "error": repr(exc)})
    raiz.destroy()
    return resultados


# ------------------------------------------------------------------ capturas CLI
def renderizar_terminal(lineas: list[str], ruta: Path, titulo: str,
                        max_lineas: int = 34) -> Path:
    """Convierte la salida de texto de la CLI en una imagen estilo terminal.

    Si la salida es muy larga, se conservan las primeras y las últimas lineas
    con un separador, para que la imagen quede en un tamaño publicable.
    """
    if len(lineas) > max_lineas:
        recorte = (max_lineas - 4) // 2
        omitidas = len(lineas) - 2 * recorte
        lineas = (
            lineas[:recorte]
            + ["", f"  … {omitidas} líneas omitidas …", ""]
            + lineas[-recorte:]
        )
    try:
        fuente = ImageFont.truetype("consola.ttf", 14)
        fuente_titulo = ImageFont.truetype("consolab.ttf", 14)
    except OSError:
        fuente = fuente_titulo = ImageFont.load_default()
    ancho = 900
    alto_linea = 21
    alto = 34 + len(lineas) * alto_linea + 26
    imagen = Image.new("RGB", (ancho, alto), (12, 12, 16))
    d = ImageDraw.Draw(imagen)
    d.rectangle([0, 0, ancho, 26], fill=(28, 32, 38))
    d.text((12, 6), titulo, font=fuente_titulo, fill=(230, 230, 230))
    y = 34
    for linea in lineas:
        color = (212, 212, 212)
        if linea.startswith("Resultado:"):
            color = (255, 121, 121) if "ATRAPADO" in linea else (130, 230, 130)
        elif "Δf = +" in linea and "<= elegido" in linea:
            color = (130, 230, 130)
        elif "Δf = -" in linea:
            color = (255, 138, 138)
        elif linea.startswith("Decisión:"):
            color = (230, 200, 120)
        elif linea.startswith("Iteración"):
            color = (140, 190, 255)
        d.text((14, y), linea, font=fuente, fill=color)
        y += alto_linea
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(ruta)
    return ruta


def captura_cli() -> list[dict]:
    """Captura la salida de la CLI en dos escenarios y la renderiza."""
    salidas = []
    escenarios_cli = [
        (
            "06_cli_caso_b_atrapado",
            ["--mapa", "B", "--variante", "steepest", "--metrica", "manhattan", "--auto"],
            "CLI: Caso B, steepest, sin mitigación",
        ),
        (
            "07_cli_penalizacion",
            ["--mapa", "B", "--variante", "steepest", "--penalizacion", "1.0",
             "--max-iter", "200", "--auto"],
            "CLI: Caso B con penalización λ = 1",
        ),
    ]
    entorno = dict(__import__("os").environ)
    entorno["PYTHONIOENCODING"] = "utf-8"
    for nombre, args, titulo in escenarios_cli:
        proc = subprocess.run(
            [sys.executable, "-m", "hillclimb.cli", *args],
            cwd=RAIZ, capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=entorno,
        )
        lineas = [l for l in proc.stdout.splitlines() if l.strip()]
        if not lineas:
            salidas.append({"nombre": nombre, "ruta": None, "error": proc.stderr[-300:]})
            continue
        ruta = renderizar_terminal(
            lineas, TEMPORAL / f"{nombre}.png", titulo
        )
        salidas.append({"nombre": nombre, "ruta": ruta})
    return salidas


# ------------------------------------------------------------------ flujo
def main() -> int:
    TEMPORAL.mkdir(parents=True, exist_ok=True)
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Tomando capturas de la GUI...")
    todas = capturas_gui()
    print("Tomando capturas de la CLI...")
    todas += captura_cli()
    # El recorte de telemetria solo contiene texto, no el lienzo: no se le
    # exigen colores del laberinto, solo que tenga contenido real.
    recorte = TEMPORAL / "02b_telemetria_detalle.png"
    if recorte.exists():
        todas.append({"nombre": "02b_telemetria_detalle", "ruta": recorte,
                      "cfg": {"exigir": ()}})

    publicadas, rechazadas = [], []
    for item in todas:
        ruta = item.get("ruta")
        if ruta is None:
            rechazadas.append((item["nombre"], item.get("error", "sin captura")))
            continue
        resultado = analizar(ruta, tuple(item.get("cfg", {}).get("exigir", ())))
        if resultado["ok"] and item.get("cfg", {}).get("banner"):
            if not analizar_banner(ruta, item["cfg"]["banner"]):
                resultado = {
                    "ok": False,
                    "motivo": f"el banner no es de tipo {item['cfg']['banner']}",
                }
        if resultado["ok"]:
            destino = DESTINO / ruta.name
            shutil.copyfile(ruta, destino)
            publicadas.append((item["nombre"], destino.name, resultado["motivo"]))
        else:
            rechazadas.append((item["nombre"], resultado["motivo"]))

    print(f"\n=== PUBLICADAS EN {DESTINO} ({len(publicadas)}) ===")
    for nombre, archivo, motivo in publicadas:
        print(f"  OK   {archivo:38s} {motivo}")
    if rechazadas:
        print(f"\n=== RECHAZADAS ({len(rechazadas)}) ===")
        for nombre, motivo in rechazadas:
            print(f"  NO   {nombre}: {motivo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
