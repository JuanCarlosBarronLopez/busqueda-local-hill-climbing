# Hill Climbing sobre un laberinto con trampas cóncavas

Demostración funcional de **búsqueda local por Hill Climbing**: interfaz
gráfica paso a paso (Tkinter), telemetría en tiempo real, dos casos de prueba
obligatorios (convergencia exitosa y atrapamiento en un máximo local), tres
mecanismos de mitigación (movimientos laterales con límite, penalización por
estancamiento y reinicios aleatorios) y un benchmark que genera las métricas,
las tablas y las figuras del reporte.

- **Problema.** Escapar de un laberinto 7 × 9. `f(s) = −d(s, g)` con `d` de
  Manhattan (por defecto) o Euclídea; el óptimo global es la meta, `f(g) = 0`.
- **Caso A** (sin trampas cóncavas): 100 % de éxito desde cualquier celda
  libre (58/58); steepest llega a `G` en 14 movimientos desde `S = (0, 0)`.
- **Caso B** (recinto en U): steepest desde `S = (3, 4)` queda atrapado en
  `(3, 5)` con `f = −3.00` y sus tres vecinos en `Δf = −1.00`; profundidad de
  barrera **7.00**; `p = 24/50 = 48.00 %` y estancamiento del 52.00 %.
- **Regla de desempate usada en todos los resultados:** orden fijo `↑ ↓ ← →`
  y, ante empates, el primero de los empatados. Con otra regla, `p` del mapa B
  oscila entre 48,00 % y 56,00 % (véase `results/sensibilidad_desempate.md`).
- **Lenguaje.** Python 3.10+ con la biblioteca estándar; `Pillow` solo para
  exportar figuras PNG y `pytest` para las pruebas.

## Requisitos e instalación

Necesitas **Python 3.10 o superior**, `Pillow` y `pytest`.

```bash
# Windows (si el alias "python" no está disponible, usar "py")
py -m pip install -r requirements.txt

# Linux / macOS
python3 -m pip install -r requirements.txt

# Linux: la interfaz gráfica necesita Tkinstalado por el sistema
#   Debian/Ubuntu:  sudo apt install python3-tk
#   Fedora:         sudo dnf install python3-tkinter
```

En Windows puedes abrir la demostración con **doble clic en `abrir_demo.bat`**
(equivale a `py run_gui.py`).

Nada más es necesario para el núcleo: `maze`, `algorithms`, `analysis`,
`benchmark`, `cli` y `tests` solo usan la biblioteca estándar.

## Estructura del repositorio

```
hill-climbing-lab/
├── README.md
├── requirements.txt            # Pillow, pytest
├── run_gui.py                  # lanza la interfaz gráfica
├── make_figures.py             # genera las 5 figuras del reporte
├── conftest.py                 # permite que pytest importe el paquete
├── .gitignore
├── hillclimb/
│   ├── maze.py                 # laberinto, vecindario (4 u 8 direcciones) y f(s)
│   ├── algorithms.py           # variantes + mitigaciones y modo sin telemetría
│   ├── analysis.py             # cuencas, barrera, desempate, bootstrap
│   ├── astar.py                # A* como contraste de memoria
│   ├── benchmark.py            # métricas, tiempos y teoría de reinicios
│   ├── cli.py                  # modo consola paso a paso
│   ├── gui.py                  # interfaz Tkinter (sin lógica de búsqueda)
│   ├── figures.py              # exportación PNG con Pillow
│   ├── vecindad8.py            # análisis de mesetas con 8 direcciones
│   ├── propiedad_mesetas.py    # verifica por qué no hay mesetas
│   └── escalabilidad.py        # mapas aleatorios 15×15 y 25×25
├── tools/verificacion_independiente.py   # segunda implementación, sin reusar el paquete
├── tools/capturas.py          # capturas de la GUI y la CLI, con control de calidad
├── tests/test_core.py          # 17 pruebas: valores de referencia y mitigaciones
├── tests/test_auditoria.py     # 28 pruebas: robustez, reproducibilidad, GUI
├── docs/modelado.md            # sección 3 del reporte (modelado formal)
├── docs/imagenes/              # capturas publicadas de la demostración
└── results/                    # metricas.csv, tablas, figuras/, entorno.md, log.txt
```

## Uso

### Interfaz gráfica (modo paso a paso)

```bash
py run_gui.py        # Windows
python3 run_gui.py   # Linux / macOS
```

- **Paso** avanza una iteración; **Auto/Pausa** ejecuta con la velocidad del
  deslizador; **Ejecutar hasta el final** termina la ejecución;
  **Reiniciar** vuelve al estado inicial; **Exportar PNG** guarda la imagen
  del lienzo; **Guardar registro** escribe `results/log.txt`.
- El lienzo pinta el mapa de calor de `f`, el rastro con flechas, el estado
  actual (marco naranja) y los `Δf` de los vecinos evaluados (verde `> 0`,
  rojo `< 0`, gris `= 0`), con borde grueso en el vecino elegido.
- **Clic izquierdo** alterna muro/libre; **clic derecho** mueve `S`. Editar el
  mapa reinicia la ejecución; un mapa incompleto (sin `S` o sin `G`) muestra
  un mensaje en lugar de un error.
- Controles disponibles: mapa (A / B / personalizado), variante
  (`simple`, `steepest`, `stochastic`, `first_choice`), métrica (Manhattan /
  Euclídea), **vecindad (4 / 8 direcciones)**, **desempate (fijo /
  aleatorio)**, mitigación (ninguna / laterales con `L` / penalización con
  `λ` / reinicios aleatorios) y semilla.

### Modo consola

```bash
py -m hillclimb.cli --mapa B --variante steepest --paso
# opciones: --metrica euclidea --vecindad 8 --desempate aleatorio
#           --laterales 20 --penalizacion 1.0 --reinicios 100
#           --semilla 2024 --max-iter 5000 --auto
```

Imprime la misma telemetría que la GUI (estado, `f`, vecinos con `Δf`, razón
de la decisión y resultado final) y espera `Enter` en cada iteración con
`--paso`.

### Pruebas

```bash
py -m pytest -q          # 43 pruebas (17 de núcleo + 26 de auditoría)
```

### Benchmark

```bash
py -m hillclimb.benchmark                      # métrica Manhattan (por defecto)
py -m hillclimb.benchmark --metrica euclidea   # repite todo con Euclídea
py -m hillclimb.benchmark --sin-extra          # solo la tabla, sin análisis extra
```

Mide las 7 configuraciones en los mapas A y B (exhaustivas desde cada celda
libre las deterministas, 1000 ejecuciones con semilla fija las aleatorias),
con calentamiento, 5 repeticiones y **mediana + IQR**. Escribe en
`results/`: `metricas.csv`, `tabla_metricas.md`, `resumen_resultados.md`,
`sensibilidad_desempate.md`, `tiempo_telemetria.md`, `entorno.md`,
`vecindad8.md`, `escalabilidad.md` y `figuras/p_vs_densidad.png`.

El benchmark es **reproducible**: dos ejecuciones consecutivas producen el
mismo CSV salvo las columnas de tiempo.

### Otras herramientas

```bash
py tools/verificacion_independiente.py --mapa A B   # segunda implementación
py -m hillclimb.vecindad8                           # informe de mesetas
py -m hillclimb.propiedad_mesetas                   # comprueba la implicación
py -m hillclimb.escalabilidad                       # mapas aleatorios
py make_figures.py                                  # las 5 figuras del reporte
py tools/capturas.py                                # capturas de la GUI y la CLI
```

## Capturas de la demostración

Las imágenes de esta sección se generan con `python tools/capturas.py`, que
toma una captura por escenario, **verifica automáticamente** que cada una
tiene contenido real (no está en blanco ni a medias) y que muestra el
resultado que le corresponde —banner verde al alcanzar la meta, rojo al
quedar atrapado—, y solo entonces la publica en `docs/imagenes/`.

### 1. Caso A: convergencia exitosa

![Caso A, ejecución completa hasta la meta](docs/imagenes/01_caso_a_exito.png)

Steepest-Ascent con orden fijo y métrica Manhattan: 14 movimientos hasta `G`,
todos con `Δf > 0`. El rastro de flechas marca el camino y el marco naranja
señala la celda actual.

### 2. Caso B: atrapamiento en el máximo local (3, 5)

![Caso B atrapado en el máximo local](docs/imagenes/02_caso_b_atrapado.png)

Desde `S = (3, 4)` el algoritmo da **un solo paso** hasta `(3, 5)` y se
detiene: los tres vecinos libres tienen `f = −4.00`, es decir `Δf = −1.00`.
La telemetría de la derecha muestra cada vecino evaluado con su `Δf` y la
razón de la parada.

### 3. Detalle de la telemetría

![Detalle del panel de telemetría](docs/imagenes/02b_telemetria_detalle.png)

Iteración, estado, `f(actual)`, la tabla de vecinos con `f(vecino)` y `Δf`
(verde si mejora, rojo si empeora, gris si es neutro), la decisión tomada y
los contadores acumulados.

### 4. Mitigación por penalización f′(s) = f(s) − λ·n(s)

![Caso B con penalización](docs/imagenes/03_penalizacion_escapa.png)

Con `λ = 1` el algoritmo sale de la trampa y alcanza la meta. Cada
estancamiento hunde `f′` del estado visitado hasta que un vecino antes
inútil se vuelve el mejor.

### 5. Mitigación por reinicios aleatorios

![Caso B con reinicios aleatorios](docs/imagenes/04_reinicios_aleatorios.png)

El primer intento desde `S` fracasa; un reinicio desde otra celda libre
alcanza la meta (con semilla `2024`, en 2 reinicios).

### 6. Mapa de calor y vecindad de 8 direcciones

![Mapa de calor con vecindad de 8](docs/imagenes/05_vecindad8_mapa_calor.png)

El sombreado va de oscuro (lejos de la meta) a claro (cerca). Con la
vecindad de 8 direcciones aparecen valores `Δf` con decimales, porque un
movimiento en diagonal cambia la distancia de forma distinta a uno cardinal.

### 7. Modo consola (CLI)

![CLI: Caso B atrapado](docs/imagenes/06_cli_caso_b_atrapado.png)

![CLI: Caso B con penalización](docs/imagenes/07_cli_penalizacion.png)

La CLI imprime exactamente la misma telemetría que la GUI, con el mismo
formato, y admite `--paso` para avanzar iteración a iteración.

## Guion de demostración (6 pasos)

1. **Caso A paso a paso.** Mapa `A`, variante `steepest`, métrica Manhattan,
   vecindad 4, desempate fijo, mitigación *Ninguna*, semilla `42`. Pulsar
   **Paso** varias veces y luego **Ejecutar hasta el final**: converge a `G`
   en **14 movimientos** con `Δf > 0` en todos. El mapa no tiene máximos
   locales.
2. **Caso B hasta el atrapamiento.** Cambiar a mapa `B` y pulsar
   **Reiniciar**: con **Paso** se ve que solo hace **1 movimiento** hasta
   `(3, 5)` y se detiene. El lienzo marca `(3, 5)` y el panel muestra el
   resultado.
3. **Mostrar los Δf negativos.** En la telemetría del último paso se leen los
   tres vecinos `↑ (2, 5)`, `↓ (4, 5)`, `← (3, 4)` con `f = −4.00` y
   `Δf = −1.00`, más la razón: *«Máximo local: todos los vecinos tienen
   Δf < 0 y f = −3.00 < 0 (óptimo global)»*. La meta está a 3 pasos, pero el
   muro de `(3, 6)` lo impide (barrera de 7.00).
4. **Activar la penalización.** Mitigación *Penalización (λ)* con `λ = 1.0` y
   **Reiniciar**; ejecutar hasta el final: escapa y alcanza la meta. Señalar
   el contador de *penalizaciones* y que `f′` hunde solo los estados
   estancados.
5. **Activar los reinicios aleatorios.** Mitigación *Reinicios aleatorios*
   con máximo 100 y semilla `2024`; **Reiniciar** y ejecutar: el primer
   intento desde `S` fracasa y un reinicio desde otra celda llega a `G` (con
   esa semilla, **2 reinicios**). Contrastar con `1/p = 2.08`.
6. **Mostrar la tabla de métricas.** Abrir `results/tabla_metricas.md` (o
   `results/resumen_resultados.md`): éxito 100 % en A frente a 48.00 % en B,
   penalización y reinicios al 100.00 % como mitigaciones, y las medianas de
   tiempo. Cerrar comparando con A* (memoria O(1) frente a la frontera de A*)
   y con la dependencia del resultado respecto al desempate.

## Resultados medidos (resumen)

| Magnitud | Valor medido |
|---|---|
| Caso A: éxito desde cualquier celda libre | 58/58 = 100.00 % (estancamiento 0.00 %) |
| Caso A: movimientos desde `S` hasta `G` (steepest) | 14 |
| Caso B: `p = \|B(g)\|/\|F\|` | 24/50 = 48.00 % (estancamiento 52.00 %) |
| Caso B: máximo local | `(3, 5)` con `f = −3.00`; los 3 vecinos con `Δf = −1.00` |
| Caso B: profundidad de barrera de `(3, 5)` | 7.00 |
| Caso B: `p` según la regla de desempate | entre 48.00 % y 56.00 % (24 permutaciones) |
| Penalización `λ = 1` desde `S` (mapa B) | escapa en 65 iteraciones (34 movimientos, 30 penalizaciones) |
| Reinicios aleatorios (semilla 2024) desde `S` | meta en 2 reinicios |
| Reinicios aleatorios, inicio uniforme | media 1.08 frente a `E[R] = (1−p)/p = 1.08` |
| Mesetas terminales (mapas A y B) | 0 con 4 y con 8 direcciones |
| Movimientos laterales solos | 0 (solo se activan junto a la penalización) |
| Variantes aleatorias en B (1000 ejecuciones, semilla 42) | 49.60 % y 50.90 % |
| Steepest + penalización / + reinicios en B | 100.00 % de éxito |

Los tiempos por ejecución (mediana de décimas de milisegundo) dependen de la
máquina: consúltese `results/metricas.csv` y `results/entorno.md` de la última
ejecución. `results/resumen_resultados.md` se regenera con cada benchmark y
cita únicamente cifras medidas.
