"""Interfaz gráfica (Tkinter) de la demostración de Hill Climbing.

La GUI **no** contiene lógica de búsqueda: solo consume los generadores
:func:`hillclimb.algorithms.hill_climbing` y
:func:`hillclimb.algorithms.random_restart` con ``next()`` para el modo paso a
paso, y pinta la telemetría que ellos producen.

Distribución:

* barra superior con todos los controles;
* panel izquierdo: lienzo con el laberinto (mapa de calor, rastro, Δf);
* panel derecho: telemetría de la iteración actual y registro histórico.
"""

from __future__ import annotations

import random
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Iterator

from .algorithms import ETIQUETAS, StepInfo, hill_climbing, random_restart
from .cli import formatear_paso
from .figures import color_calor, guardar, render
from .maze import Cell, Maze, cargar_mapa

FUENTE = "Segoe UI"
MONO = "Consolas"
TAM = 56  # tamaño de celda en el lienzo
OX, OY = 12, 12

COLORES = {
    "muro": "#2c2f33",
    "linea": "#c8ccd2",
    "texto": "#20242a",
    "actual": "#e65100",
    "elegido": "#1565c0",
    "positivo": "#1b5e20",
    "negativo": "#b71c1c",
    "cero": "#757575",
    "inicio": "#2e7d32",
    "meta": "#f5b000",
    "rastro": "#1565c0",
    "tenue": "#9aa5b1",
}

VARIANTES = ("simple", "steepest", "stochastic", "first_choice")
MITIGACIONES = ("Ninguna", "Laterales (L)", "Penalización (λ)", "Reinicios aleatorios")
#: Etiquetas de la barra de título según el estado alcanzado.
ETIQUETAS_ESTADO = dict(ETIQUETAS)
RUTA_LOG = Path(__file__).resolve().parent.parent / "results" / "log.txt"
RUTA_FIGURAS = Path(__file__).resolve().parent.parent / "results" / "figuras"


def _rgb(hexadecimal: str) -> tuple[int, int, int]:
    return tuple(int(hexadecimal[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


class Aplicacion:
    """Ventana principal de la demostración."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Hill Climbing — laberinto con trampas cóncavas")
        root.minsize(1180, 720)
        root.option_add("*Font", f"{{{FUENTE}}} 10")

        self.mapa_nombre = "A"
        self.maze: Maze = cargar_mapa("A")
        self.maze_personalizado: Maze = cargar_mapa("Personalizado")
        self.gen: Iterator[StepInfo] | None = None
        self.info: StepInfo | None = None
        self.recorrido: list[tuple[str, Cell]] = []
        self.historial: list[str] = []
        self.auto_activo = False
        self.tarea_auto: str | None = None
        self.tot_estancamientos = 0
        self.tot_penalizaciones = 0
        self.max_reinicios = 0
        self.reinicio_actual = 0

        self._construir_controles(root)
        self._construir_lienzo(root)
        self._construir_paneles(root)
        self._reiniciar()

    # ------------------------------------------------------------------ interfaz
    def _construir_controles(self, root: tk.Tk) -> None:
        barra = ttk.Frame(root, padding=8)
        barra.pack(fill="x")

        self.var_mapa = tk.StringVar(value="A (sin trampas)")
        self.var_variante = tk.StringVar(value="steepest")
        self.var_metrica = tk.StringVar(value="Manhattan")
        self.var_vecindad = tk.StringVar(value="4")
        self.var_desempate = tk.StringVar(value="fijo")
        self.var_mitigacion = tk.StringVar(value=MITIGACIONES[0])
        self.var_param = tk.StringVar(value="20")
        self.var_semilla = tk.StringVar(value="42")
        self.var_velocidad = tk.IntVar(value=10)
        self.var_estado_banner = tk.StringVar(value="Pulsa «Paso» para avanzar iteración a iteración.")

        ttk.Label(barra, text="Mapa:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Combobox(
            barra, textvariable=self.var_mapa, state="readonly", width=18,
            values=["A (sin trampas)", "B (trampa en U)", "Personalizado"],
        ).grid(row=0, column=1, sticky="w", padx=2)
        self.var_mapa.trace_add("write", lambda *_: self._cambiar_mapa())

        ttk.Label(barra, text="Variante:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Combobox(
            barra, textvariable=self.var_variante, state="readonly", width=13,
            values=list(VARIANTES),
        ).grid(row=0, column=3, sticky="w", padx=2)

        ttk.Label(barra, text="Métrica:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Combobox(
            barra, textvariable=self.var_metrica, state="readonly", width=13,
            values=["Manhattan", "Euclídea"],
        ).grid(row=0, column=5, sticky="w", padx=2)

        ttk.Label(barra, text="Vecindad:").grid(row=0, column=6, sticky="e", padx=2)
        ttk.Combobox(
            barra, textvariable=self.var_vecindad, state="readonly", width=6,
            values=["4", "8"],
        ).grid(row=0, column=7, sticky="w", padx=2)

        ttk.Label(barra, text="Desempate:").grid(row=0, column=8, sticky="e", padx=2)
        ttk.Combobox(
            barra, textvariable=self.var_desempate, state="readonly", width=11,
            values=["fijo", "aleatorio"],
        ).grid(row=0, column=9, sticky="w", padx=2)

        ttk.Label(barra, text="Mitigación:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Combobox(
            barra, textvariable=self.var_mitigacion, state="readonly", width=18,
            values=list(MITIGACIONES),
        ).grid(row=1, column=1, sticky="w", padx=2)

        self.etiqueta_param = ttk.Label(barra, text="L (laterales):")
        self.etiqueta_param.grid(row=1, column=2, sticky="e", padx=2)
        ttk.Spinbox(
            barra, textvariable=self.var_param, from_=0, to=1000, width=6,
        ).grid(row=1, column=3, sticky="w", padx=2)

        ttk.Label(barra, text="Semilla:").grid(row=1, column=4, sticky="e", padx=2)
        ttk.Entry(barra, textvariable=self.var_semilla, width=8).grid(
            row=1, column=5, sticky="w", padx=2
        )

        botones = ttk.Frame(barra)
        botones.grid(row=2, column=0, columnspan=10, pady=(8, 0), sticky="w")
        ttk.Button(botones, text="Paso", command=self.paso).pack(side="left", padx=2)
        self.boton_auto = ttk.Button(botones, text="Auto/Pausa", command=self.alternar_auto)
        self.boton_auto.pack(side="left", padx=2)
        ttk.Button(botones, text="Ejecutar hasta el final", command=self.ejecutar_final).pack(
            side="left", padx=2
        )
        ttk.Button(botones, text="Reiniciar", command=self._reiniciar).pack(side="left", padx=2)
        ttk.Button(botones, text="Exportar PNG", command=self.exportar_png).pack(side="left", padx=2)
        ttk.Button(botones, text="Guardar registro", command=self.guardar_registro).pack(
            side="left", padx=2
        )
        ttk.Label(botones, text="Velocidad:").pack(side="left", padx=(16, 2))
        ttk.Scale(
            botones, variable=self.var_velocidad, from_=1, to=20, length=110,
            orient="horizontal",
        ).pack(side="left")

        for var in (
            self.var_variante, self.var_metrica, self.var_vecindad,
            self.var_desempate, self.var_mitigacion,
        ):
            var.trace_add("write", lambda *_: self._reiniciar())
        self.var_param.trace_add("write", lambda *_: self._reiniciar())
        self.var_mitigacion.trace_add("write", lambda *_: self._ajustar_parametro())
        self.var_semilla.trace_add("write", lambda *_: self._reiniciar())

    def _construir_lienzo(self, root: tk.Tk) -> None:
        marco = ttk.Frame(root, padding=(8, 0, 8, 8))
        marco.pack(side="left", fill="both", expand=True)
        ancho = 2 * OX + self.maze.C * TAM
        alto = 2 * OY + self.maze.R * TAM + 26
        self.lienzo = tk.Canvas(
            marco, width=ancho, height=alto, bg="#f7f8fa", highlightthickness=0
        )
        self.lienzo.pack()
        self.lienzo.bind("<Button-1>", self._clic_izquierdo)
        self.lienzo.bind("<Button-3>", self._clic_derecho)
        ttk.Label(
            marco, foreground="#555b63", wraplength=ancho, justify="left",
            text="Clic izquierdo: alterna muro/libre · Clic derecho: mueve S · "
                 "La edición reinicia la ejecución",
        ).pack(anchor="w", pady=(6, 0))

    def _construir_paneles(self, root: tk.Tk) -> None:
        der = ttk.Frame(root, padding=(0, 0, 8, 8), width=460)
        der.pack(side="right", fill="both")
        der.pack_propagate(False)

        self.banner = ttk.Label(
            der, textvariable=self.var_estado_banner, anchor="center",
            background="#eceff1", foreground="#20242a", padding=6,
        )
        self.banner.pack(fill="x")

        tele = ttk.LabelFrame(der, text="Telemetría", padding=6)
        tele.pack(fill="both", expand=True, pady=(6, 0))
        self.texto_tele = tk.Text(
            tele, height=17, wrap="word", font=(MONO, 10), state="disabled",
            background="#fbfcfd", foreground="#20242a",
        )
        self.texto_tele.pack(fill="both", expand=True)
        self.contadores = ttk.Label(
            der, anchor="w", foreground="#37474f",
            text="Iteraciones: 0 | Movimientos: 0 | Reinicios: 0 | "
                 "Estancamientos: 0 | Penalizaciones: 0",
        )
        self.contadores.pack(fill="x", pady=(6, 4))

        reg = ttk.LabelFrame(der, text="Registro", padding=6)
        reg.pack(fill="both", expand=True, pady=(6, 0))
        self.texto_reg = tk.Text(
            reg, wrap="word", font=(MONO, 9), state="disabled",
            background="#fbfcfd", foreground="#20242a",
        )
        barra = ttk.Scrollbar(reg, command=self.texto_reg.yview)
        barra.pack(side="right", fill="y")
        self.texto_reg.config(yscrollcommand=barra.set)
        self.texto_reg.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ estado
    def _ajustar_parametro(self) -> None:
        """Ajusta la etiqueta y el valor por defecto del parámetro de mitigación."""
        mitig = self.var_mitigacion.get()
        if mitig.startswith("Laterales"):
            self.etiqueta_param.config(text="L (laterales):")
            self.var_param.set("20")
        elif mitig.startswith("Penalización"):
            self.etiqueta_param.config(text="λ (penalización):")
            self.var_param.set("1.0")
        elif mitig.startswith("Reinicios"):
            self.etiqueta_param.config(text="Máx. reinicios:")
            self.var_param.set("100")
        else:
            self.etiqueta_param.config(text="(sin parámetro)")

    def _cambiar_mapa(self) -> None:
        nombre = self.var_mapa.get()
        if nombre.startswith("A"):
            self.mapa_nombre = "A"
            self.maze = cargar_mapa("A")
        elif nombre.startswith("B"):
            self.mapa_nombre = "B"
            self.maze = cargar_mapa("B")
        else:
            self.mapa_nombre = "Personalizado"
            self.maze = self.maze_personalizado.copy()
        self._reiniciar()

    def _semilla(self) -> random.Random:
        texto = self.var_semilla.get().strip()
        return random.Random(int(texto)) if texto.lstrip("-").isdigit() else random.Random()

    def _params(self) -> dict:
        """Parámetros del algoritmo a partir de los controles."""
        metric = "manhattan" if self.var_metrica.get().startswith("Manh") else "euclidea"
        params = dict(
            variant=self.var_variante.get(),
            metric=metric,
            vecindad=int(self.var_vecindad.get()),
            desempate=self.var_desempate.get(),
        )
        mitig = self.var_mitigacion.get()
        self.max_reinicios = 0
        if mitig.startswith("Laterales"):
            params["sideways_limit"] = max(int(float(self.var_param.get() or 0)), 0)
        elif mitig.startswith("Penalización"):
            params["penalty_lambda"] = max(float(self.var_param.get() or 0.0), 0.0)
        elif mitig.startswith("Reinicios"):
            self.max_reinicios = max(int(float(self.var_param.get() or 1)), 1)
        return params

    def _mapa_valido(self) -> bool:
        """¿Tiene el mapa actual una S y una G? Si no, se avisa en lugar de fallar."""
        return self.maze.start is not None and self.maze.goal is not None

    def _nuevo_generador(self) -> None:
        kw = self._params()
        rng = self._semilla()
        inicio = self.maze.start
        if inicio is None:  # el mapa no tiene S: no hay ejecución que lanzar
            self.gen = None
            return
        if self.max_reinicios:
            self.gen = random_restart(
                self.maze, inicio, rng, max_restarts=self.max_reinicios, **kw
            )
        else:
            self.gen = hill_climbing(self.maze, inicio, rng=rng, **kw)

    def _reiniciar(self, *_) -> None:
        """Vuelve al estado inicial conservando el mapa (ya editado)."""
        self.auto_stop()
        self.recorrido = []
        self.historial = []
        self.info = None
        self.tot_estancamientos = 0
        self.tot_penalizaciones = 0
        self.reinicio_actual = 0
        self.gen = None
        self.texto_tele.config(state="normal")
        self.texto_tele.delete("1.0", "end")
        self.texto_tele.config(state="disabled")
        self.texto_reg.config(state="normal")
        self.texto_reg.delete("1.0", "end")
        self.texto_reg.config(state="disabled")
        self._actualizar_contadores(0, 0, 0)
        self._dibujar()
        if not self._mapa_valido():
            # Mensaje amigable en lugar de una excepción de Maze.
            self.banner.config(background="#ffe0b2", foreground="#7a4b00")
            self.var_estado_banner.set(
                "Mapa incompleto: falta marcar la celda inicial S o la meta G. "
                "Usa el clic derecho para colocar S sobre una celda libre."
            )
            return
        self._nuevo_generador()
        self.banner.config(background="#eceff1", foreground="#20242a")
        self.var_estado_banner.set(
            "En ejecución: pulsa «Paso» para avanzar iteración a iteración."
        )

    # ------------------------------------------------------------------ ejecución
    def paso(self) -> bool:
        """Avanza UNA iteración; devuelve ``True`` si la ejecución continúa."""
        if self.gen is None:
            return False
        try:
            info = next(self.gen)
        except StopIteration:
            # Con reinicios, el generador sigue vivo tras un intento fallido:
            # solo aquí se acaba realmente la demostración.
            self.auto_stop()
            if self.info is not None:
                self.var_estado_banner.set(
                    f"Demostración finalizada · {ETIQUETAS[self.info.status]} "
                    f"en {self.info.restart} reinicio(s)."
                )
            else:
                self.var_estado_banner.set("Demostración finalizada.")
            return False
        self.info = info
        if info.chosen is not None:
            for e in info.evaluations:
                if e.cell == info.chosen:
                    self.recorrido.append((e.arrow, e.cell))
                    break
        if info.decision.startswith("Estancado"):
            self.tot_penalizaciones += 1
        if info.status in ("local_max", "plateau"):
            self.tot_estancamientos += 1
        if info.restart != self.reinicio_actual:
            self.reinicio_actual = info.restart
            self._anadir_registro(f"——— Reinicio {info.restart} ———")
            if self.recorrido:
                self.recorrido = []  # cada reinicio dibuja su propio camino
        self._anadir_registro(formatear_paso(info))
        self._mostrar_telemetria(info)
        self._dibujar()
        if info.status != "running":
            self.var_estado_banner.set(f"{ETIQUETAS[info.status]} · {info.decision}")
            if info.status == "goal":
                self.banner.config(background="#c8e6c9", foreground="#1b5e20")
            else:
                self.banner.config(background="#ffcdd2", foreground="#b71c1c")
            if self.max_reinicios == 0:
                # Sin reinicios, un estado terminal cierra la demostración.
                self.auto_stop()
                return False
        return True

    def alternar_auto(self) -> None:
        if self.auto_activo:
            self.auto_stop()
        else:
            self.auto_activo = True
            self.boton_auto.config(text="Pausa")
            self._bucle_auto()

    def _bucle_auto(self) -> None:
        if not self.auto_activo:
            return
        if not self.paso():
            return
        velocidad = max(1, self.var_velocidad.get())
        delay = max(50, 1050 - velocidad * 50)
        self.tarea_auto = self.root.after(delay, self._bucle_auto)

    def auto_stop(self) -> None:
        self.auto_activo = False
        self.boton_auto.config(text="Auto/Pausa")
        if self.tarea_auto is not None:
            self.root.after_cancel(self.tarea_auto)
            self.tarea_auto = None

    def ejecutar_final(self) -> None:
        self.auto_stop()
        for _ in range(100_000):
            if not self.paso():
                return

    # ------------------------------------------------------------------ pintado
    def _color_calor(self) -> dict[Cell, tuple[int, int, int]]:
        metric = "manhattan" if self.var_metrica.get().startswith("Manh") else "euclidea"
        if self.maze.goal is None:
            return {}  # mapa sin meta: nada que colorear
        return color_calor(self.maze, metric)

    def _dibujar(self) -> None:
        self.lienzo.delete("all")
        cal = self._color_calor()
        info = self.info
        elegido = info.chosen if info else None
        evaluadas = {e.cell: e for e in (info.evaluations if info else [])}
        actual = info.current if info else None

        for r in range(self.maze.R):
            for c in range(self.maze.C):
                x0, y0 = OX + c * TAM, OY + r * TAM
                x1, y1 = x0 + TAM, y0 + TAM
                celda = (r, c)
                if self.maze.grid[r][c] == "#":
                    self.lienzo.create_rectangle(
                        x0, y0, x1, y1, fill=COLORES["muro"], outline=COLORES["muro"]
                    )
                    continue
                base = cal.get(celda, (247, 248, 250))
                self.lienzo.create_rectangle(
                    x0, y0, x1, y1, fill="#%02x%02x%02x" % base, outline=COLORES["linea"]
                )
                if celda in evaluadas:
                    e = evaluadas[celda]
                    color = (
                        COLORES["positivo"] if e.delta > 0
                        else COLORES["negativo"] if e.delta < 0
                        else COLORES["cero"]
                    )
                    self.lienzo.create_text(
                        (x0 + TAM / 2, y0 + 13), text=f"Δ{e.delta:+.2f}",
                        fill=color, font=(FUENTE, 9, "bold"),
                    )
                    grosor = 4 if celda == elegido else 2
                    self.lienzo.create_rectangle(
                        x0 + 1, y0 + 1, x1 - 1, y1 - 1, outline=color, width=grosor
                    )

        # rastro con flechas
        for arrow, celda in self.recorrido:
            r, c = celda
            cx, cy = OX + c * TAM + TAM / 2, OY + r * TAM + TAM / 2
            self.lienzo.create_text(
                (cx, cy), text=arrow, fill=COLORES["rastro"],
                font=("Segoe UI Symbol", 20, "bold"),
            )

        # S y G (una celda sin marcar simplemente no se dibuja)
        marcadores = (
            (self.maze.start, "S", COLORES["inicio"]),
            (self.maze.goal, "G", COLORES["meta"]),
        )
        for pos_marca, letra, color_marca in marcadores:
            if pos_marca is None:
                continue
            r, c = pos_marca
            cx, cy = OX + c * TAM + TAM / 2, OY + r * TAM + TAM / 2
            self.lienzo.create_oval(
                cx - 18, cy - 18, cx + 18, cy + 18,
                fill=color_marca, outline="white", width=2,
            )
            self.lienzo.create_text(
                (cx, cy), text=letra, fill="white", font=(FUENTE, 14, "bold")
            )

        if actual:
            r, c = actual
            self.lienzo.create_rectangle(
                OX + c * TAM + 2, OY + r * TAM + 2,
                OX + (c + 1) * TAM - 2, OY + (r + 1) * TAM - 2,
                outline=COLORES["actual"], width=4,
            )
        if info and info.current != elegido and elegido:
            r, c = elegido
            self.lienzo.create_rectangle(
                OX + c * TAM + 3, OY + r * TAM + 3,
                OX + (c + 1) * TAM - 3, OY + (r + 1) * TAM - 3,
                outline=COLORES["elegido"], width=3,
            )

        self.lienzo.create_text(
            OX, 2 * OY + self.maze.R * TAM + 6, anchor="nw", fill="#555b63",
            font=(FUENTE, 9),
            text="Claro = cerca de la meta · marco naranja = estado actual · "
                 "marco azul = vecino elegido",
        )

    # ------------------------------------------------------------------ textos
    def _mostrar_telemetria(self, info: StepInfo) -> None:
        self.texto_tele.config(state="normal")
        self.texto_tele.delete("1.0", "end")
        self.texto_tele.insert("end", formatear_paso(info))
        self.texto_tele.config(state="disabled")
        self._actualizar_contadores(info.iteration, info.moves, info.restart)

    def _anadir_registro(self, texto: str) -> None:
        self.historial.append(texto)
        self.texto_reg.config(state="normal")
        self.texto_reg.insert("end", texto + "\n" + "-" * 40 + "\n")
        self.texto_reg.see("end")
        self.texto_reg.config(state="disabled")

    def _actualizar_contadores(self, iteracion: int, movimientos: int, reinicios: int) -> None:
        self.contadores.config(
            text=(
                f"Iteraciones: {iteracion} | Movimientos: {movimientos} | "
                f"Reinicios: {reinicios} | Estancamientos: {self.tot_estancamientos} | "
                f"Penalizaciones: {self.tot_penalizaciones}"
            )
        )

    # ------------------------------------------------------------------ eventos
    def _celda_de_evento(self, event: tk.Event) -> Cell | None:
        c = (event.x - OX) // TAM
        r = (event.y - OY) // TAM
        if 0 <= r < self.maze.R and 0 <= c < self.maze.C:
            return (r, c)
        return None

    def _clic_izquierdo(self, event: tk.Event) -> None:
        celda = self._celda_de_evento(event)
        if celda and self.maze.toggle_wall(celda):
            if self.mapa_nombre == "Personalizado":
                self.maze_personalizado = self.maze.copy()
            self._reiniciar()
            self.var_estado_banner.set(
                f"Mapa editado en {celda}: ejecución reiniciada."
            )

    def _clic_derecho(self, event: tk.Event) -> None:
        celda = self._celda_de_evento(event)
        if celda and self.maze.set_start(celda):
            self.maze_personalizado = self.maze.copy()
            if self.mapa_nombre != "Personalizado":
                self.var_mapa.set("Personalizado")  # dispara _cambiar_mapa()
            else:
                self._reiniciar()
            self.var_estado_banner.set(f"Nuevo inicio S = {celda}: ejecución reiniciada.")

    # ------------------------------------------------------------------ archivos
    def exportar_png(self, ruta: Path | None = None) -> None:
        """Exporta el estado actual del lienzo a un PNG con Pillow.

        Si ``ruta`` es ``None`` se pregunta al usuario con un diálogo; pasarla
        explícitamente permite exportar sin interacción (pruebas automáticas).
        """
        info = self.info
        if not self._mapa_valido():
            self.var_estado_banner.set(
                "No se puede exportar: el mapa necesita una S y una G."
            )
            return
        if ruta is None:
            ruta_str = filedialog.asksaveasfilename(
                parent=self.root,
                title="Exportar PNG",
                initialdir=str(RUTA_FIGURAS if RUTA_FIGURAS.exists() else Path.home()),
                initialfile=f"captura_mapa_{self.mapa_nombre}.png",
                defaultextension=".png",
            )
            if not ruta_str:
                return  # el usuario canceló
            ruta = Path(ruta_str)
        titulo = f"Captura desde la GUI - mapa {self.mapa_nombre}, variante {self.var_variante.get()}"
        subtitulo = "Estado actual de la demostración de Hill Climbing."
        img = render(
            self.maze,
            titulo,
            subtitulo,
            rastro=list(self.recorrido),
            actual=info.current if info else None,
            evaluaciones=info.evaluations if info else None,
            elegido=info.chosen if info else None,
            metric="manhattan" if self.var_metrica.get().startswith("Manh") else "euclidea",
            pie="Generado con hillclimb.figures.render (Pillow).",
        )
        destino = guardar(img, ruta)
        self.var_estado_banner.set(f"Imagen guardada en {destino}")

    def guardar_registro(self) -> None:
        """Guarda el historial de iteraciones en ``results/log.txt``."""
        RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)
        encabezado = [
            f"Mapa {self.mapa_nombre} ({self.maze.name})",
            f"Variante {self.var_variante.get()} | métrica {self.var_metrica.get()} | "
            f"mitigación {self.var_mitigacion.get()} ({self.var_param.get()}) | "
            f"semilla {self.var_semilla.get()}",
            "-" * 60,
        ]
        RUTA_LOG.write_text(
            "\n".join(encabezado + self.historial) + "\n", encoding="utf-8"
        )
        self.var_estado_banner.set(f"Registro guardado en {RUTA_LOG}")


def main() -> None:
    """Lanza la interfaz gráfica."""
    root = tk.Tk()
    Aplicacion(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
