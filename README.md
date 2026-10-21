# Hill Climbing sobre un laberinto con trampas cóncavas

> **Búsqueda local, en vivo y con números.** Una demostración funcional de
> Hill Climbing: interfaz gráfica paso a paso, telemetría completa, dos casos
> obligatorios (éxito y atasco), tres mecanismos de mitigación y un benchmark
> reproducible con verificación independiente de todas las cifras.

---

## 📋 Resumen ejecutivo

**El problema.** Escapar de un laberinto 7 × 9 modelado como problema de
optimización: maximizar `f(s) = −d(s, g)`. En el mapa B, una **trampa cóncava**
en forma de U deja al algoritmo sin salida.

**La herramienta.** Hill Climbing, la búsqueda local más simple: en cada paso
mueve al vecino que más mejore `f`. Memoria O(1), sin planificación, sin vuelta
atrás.

**El resultado.** La sencillez se paga: en el mapa B el algoritmo se atasca en
el **52 %** de los puntos de partida. Las mitigaciones lo resuelven —penalización
y reinicios aleatorios alcanzan el **100 %**— y el coste de cada una queda
medido.

**El hallazgo.** El resultado no es solo una propiedad del mapa: **depende de la
regla de desempate** (entre 48 % y 56 %) y de la métrica (48 % con Manhattan,
56 % con Euclídea). Verificamos además, contra la intuición teórica, que **las
mesetas no existen** con la regla de no cortar esquinas, y explicamos por qué.

| Magnitud | Valor medido |
|---|---|
| Caso A (sin trampas): éxito desde cualquier celda | **58/58 = 100,00 %** |
| Caso B (trampa en U): `p = \|B(g)\|/\|F\|` | **24/50 = 48,00 %** |
| Caso B: estancamiento | **52,00 %** (26 celdas en el mismo sumidero) |
| Profundidad de barrera del máximo local (3, 5) | **7,00** |
| Penalización `λ = 1` | escapa en **65 iteraciones**; éxito **100 %** |
| Reinicios aleatorios | éxito **100 %**; **1,14** de media vs **1,08** teóricos |
| A\* como contraste (misma información) | camino óptimo **16**, frontera máx. 7 |

---

## 🎯 El problema

Dos mapas de 7 × 9 (`S` = inicio, `G` = meta, `#` = muro):

```
Caso A — sin trampas cóncavas          Caso B — recinto en U
S . . . . . . . .                      . . . . . . . . .
. . # . . . . . .                      . . # # # # # . .
. . . . # . . # .                      . . . . . . # . .
. . . . . . . . .                      . . . . S . # . G
. # . . . . # . .                      . . . . . . # . .
. . . . . . . . .                      . . # # # # # . .
. . . . . . . . G                      . . . . . . . . .
```

En el mapa A, **no existe ningún máximo local**: desde cualquier celda se llega
a la meta. Es el control.

En el mapa B, el recinto en U se abre **mirando en dirección contraria a la
meta**. El gradiente de `f` conduce al fondo del recinto, y la salida exige
alejarse primero de `G` — algo que Hill Climbing nunca hace.

---

## 🧠 El algoritmo

### La analogía

> Imagina escalar una montaña con **niebla total**. Solo ves el suelo bajo tus
> pies y un paso a cada lado. No ves la cima. Entonces haces lo razonable:
> miras las casillas contiguas y das un paso a la que esté más alta. Repites.
> Cuando ninguna sube, te quedas donde estás.

Eso es todo. Hill Climbing no planifica, no recuerda por dónde vino y no
retrocede.

### Las cuatro piezas

| Pieza | Definición |
|---|---|
| **Estado** `s` | una celda libre `(fila, columna)` |
| **Vecindario** `N(s)` | las celdas contiguas pisables, en orden fijo `↑ ↓ ← →` |
| **Aptitud** `f(s)` | `f(s) = −d(s, g)`: maximizar `f` es acercarse a la meta |
| **Regla de avance** | a qué vecino saltar (las cuatro variantes) |

El óptimo global es la meta, con `f(g) = 0`. Todo lo demás es negativo.

### El bucle

```
1. ¿Estoy en la meta?                     → sí: TERMINO (óptimo global)
2. Mido f de cada vecino, calculo Δf = f(vecino) − f(actual)
3. ¿Algún vecino con Δf > 0?              → sí: me muevo, vuelvo a 1
4. Ninguno mejora                         → TERMINO (máximo local o meseta)
```

### Por qué se atasca

En `(3, 5)` del mapa B, con métrica Manhattan:

| Vecino | `f(vecino)` | `Δf` |
|---|---|---|
| ↑ (2, 5) | −4,00 | **−1,00** |
| ↓ (4, 5) | −4,00 | **−1,00** |
| ← (3, 4) | −4,00 | **−1,00** |

La meta está a tres pasos en línea recta, pero hay un muro en `(3, 6)`. Salir
exigiría **bajar** `f`, y el algoritmo no acepta eso. **No es un bug: es la
naturaleza de la búsqueda local.**

---

## 🖥️ Demostración visual

Las siguientes capturas se generan con `py tools/capturas.py`, que
**verifica automáticamente** cada imagen antes de publicarla: rechaza las que
están en blanco, las que no contienen los elementos del lienzo (marcador `S`,
meta `G`, estado actual, vecino elegido) y las cuyo banner de estado no
corresponde al resultado esperado —verde al alcanzar la meta, rojo al quedar
atrapado—.

### 1. Caso A: convergencia exitosa

![Caso A, ejecución completa hasta la meta](docs/imagenes/01_caso_a_exito.png)

Steepest-Ascent, orden fijo, métrica Manhattan. **14 movimientos** hasta `G`,
todos con `Δf > 0`. El rastro de flechas marca el camino, el marco naranja
señala la celda actual y el banner verde confirma la meta alcanzada.

### 2. Caso B: atrapamiento en el máximo local (3, 5)

![Caso B atrapado en el máximo local](docs/imagenes/02_caso_b_atrapado.png)

Desde `S = (3, 4)` el algoritmo da **un solo paso** hasta `(3, 5)` y se
detiene. Los tres vecinos libres tienen `f = −4,00`, es decir `Δf = −1,00`. La
telemetría de la derecha muestra cada vecino evaluado con su `f(vecino)`, su
`Δf` y la razón exacta de la parada.

### 3. Detalle de la telemetría

![Detalle del panel de telemetría](docs/imagenes/02b_telemetria_detalle.png)

Iteración, movimientos, estado actual con `f(actual)`, la tabla de vecinos con
marca de elegido, la decisión tomada, el resultado final y los contadores
acumulados (estancamientos, penalizaciones, reinicios).

### 4. Mitigación por penalización f′(s) = f(s) − λ·n(s)

![Caso B con penalización](docs/imagenes/03_penalizacion_escapa.png)

Con `λ = 1` el algoritmo **sale de la trampa** y alcanza la meta. Cada
estancamiento incrementa `n(s)` y hunde `f′(s)`, hasta que un vecino antes
inútil se convierte en el mejor.

### 5. Mitigación por reinicios aleatorios

![Caso B con reinicios aleatorios](docs/imagenes/04_reinicios_aleatorios.png)

El primer intento desde `S` fracasa; un reinicio desde otra celda libre alcanza
la meta. Con semilla `2024`, en **2 reinicios**.

### 6. Mapa de calor y vecindad de 8 direcciones

![Mapa de calor con vecindad de 8](docs/imagenes/05_vecindad8_mapa_calor.png)

El sombreado va de oscuro (lejos de la meta) a claro (cerca). Con la vecindad
de 8 direcciones aparecen valores `Δf` con decimales, porque un movimiento en
diagonal cambia la distancia de forma distinta a uno cardinal.

### 7. Modo consola (CLI)

![CLI: Caso B atrapado](docs/imagenes/06_cli_caso_b_atrapado.png)

![CLI: Caso B con penalización](docs/imagenes/07_cli_penalizacion.png)

La CLI imprime **exactamente la misma telemetría** que la GUI, con el mismo
formato, y admite `--paso` para avanzar iteración a iteración.

---

## 📊 Resultados medidos

### Tabla principal (mapa B, métrica Manhattan, semilla 42)

| Configuración | Ejecuciones | Éxito | Estancamiento | Iter. medias (éxito) | Tiempo mediana |
|---|---|---|---|---|---|
| HC simple | 50 | 48,00 % | 52,00 % | 5,21 | 0,0427 ms |
| HC steepest | 50 | 48,00 % | 52,00 % | 5,21 | 0,0456 ms |
| HC estocástico | 1000 | 49,60 % | 50,40 % | 5,57 | 0,0518 ms |
| HC first-choice | 1000 | 50,90 % | 49,10 % | 5,71 | 0,0506 ms |
| Steepest + laterales L=20 | 50 | 48,00 % | 52,00 % | 5,21 | 0,0461 ms |
| Steepest + penalización λ=1 | 50 | **100,00 %** | 0,00 % | 38,04 | 0,3009 ms |
| Steepest + reinicios | 1000 | **100,00 %** | 0,00 % | 5,23 | 0,1042 ms |

Las configuraciones deterministas se ejecutan **exhaustivamente desde cada
celda libre**, así que su tasa de éxito es exactamente `p = |B(g)|/|F|`. Las
aleatorias usan 1000 ejecuciones con semilla fija. Los tiempos son **mediana e
IQR sobre 5 repeticiones con calentamiento**.

### La variante *simple* frente a la trampa

Elegir el primer ascenso disponible en lugar del más pronunciado **cambia el
camino pero no la topología**: ambas variantes caen en el mismo máximo local.
La trampa es una propiedad del mapa, no de la regla de avance.

### Teoría frente a medición (reinicios aleatorios)

Con `p = 48,00 %` y muestreo uniforme de la celda inicial:

| Magnitud | Teoría | Medido |
|---|---|---|
| Ejecuciones totales `E[K] = 1/p` | 2,08 | — |
| Reinicios `E[R] = (1−p)/p` | **1,08** | **1,14** (IC 95 %: 104,50 %–124,50 %) |
| Éxito tras 2 intentos | 72,96 % | 71,50 % |
| Éxito tras 5 intentos | 96,20 % | 95,50 % |

El intervalo de confianza (bootstrap, 5000 remuestreos) **contiene el valor
teórico**: el modelo predice lo que se mide.

### Contraste con A\*

Hill Climbing guarda un único estado (**memoria O(1)**). A\*, con la misma
heurística de Manhattan, expande 48 nodos y alcanza una frontera máxima de 7
celdas para garantizar el camino óptimo de 16 movimientos. **Es un intercambio
explícito de garantía por recurso.**

---

## 🔬 Análisis del paisaje

### Cuencas de atracción y barrera

Ejecutando *steepest* desde cada celda libre:

- **Mapa A:** `p = 58/58 = 100 %`, estancamiento 0 %.
- **Mapa B:** `p = 24/50 = 48 %`. Las 26 celdas atrapadas caen **todas en el
  mismo sumidero** `(3, 5)`.
- **Profundidad de barrera** de ese máximo local: **7,00**, porque todo camino
  de escape pasa por `(0, 1)` o `(6, 1)`, ambas con `f = −10`.

### Las mesetas no existen (resultado negativo verificado)

Con 4 direcciones y métrica Manhattan o Euclídea, `Δf ≠ 0` siempre: cualquier
movimiento cambia la distancia en una cantidad distinta de cero. Con **8
direcciones** la teoría anuncia mesetas, porque un diagonal puede dejar la
distancia invariante.

**Medido: no ocurre.** Verificamos la implicación celda por celda en 8 mapas
(A, B y seis aleatorios) y con las dos métricas, **0 excepciones**:

> Si una celda tiene un vecino lateral (`Δf = 0`) y la regla es *no cortar
> esquinas*, entonces las dos celdas cardinales adyacentes existen libres y
> tienen `Δf > 0`. Luego «tener lateral» implica «tener ascendente», y una
> meseta (sin ascendente pero con lateral) es **inalcanzable**.

Consecuencia práctica: los movimientos laterales **nunca se activan solos** en
estos mapas. Solo se activan cuando otra mitigación crea empates.

### El resultado depende del desempate

Cuando dos vecinos empatan en `Δf`, la elección es una decisión de diseño:

| Regla de desempate | `p` en el mapa B |
|---|---|
| Orden fijo `↑ ↓ ← →`, primero de los empatados (**el usado aquí**) | **48,00 %** |
| Las 24 permutaciones del orden | 48,00 % – 56,00 % (σ = 3,27) |
| Desempate aleatorio entre empatados | 48,00 % – 56,00 % (media 50,30 %) |

Por eso todo el repositorio **fija una regla y la declara** en cada resultado.

### Escalabilidad

Mapas aleatorios de 15 × 15 y 25 × 25 con densidades de muro crecientes:

| Mapa | Densidad | `p` steepest | Penalización | Reinicios |
|---|---|---|---|---|
| 15 × 15 | 10 % | 59,13 % | 100 % | 100 % |
| 15 × 15 | 20 % | 3,89 % | 98,89 % | 98,50 % |
| 25 × 25 | 10 % | 24,87 % | 99,82 % | 100 % |
| 25 × 25 | 20 % | 1,20 % | 100 % | 72,00 % |

Al subir la densidad, `p` se derrumba y las mitigaciones mantienen el éxito.
La única excepción (72 %, reinicios en 25 × 25 al 20 %) es honesta: con
`p ≈ 1,2 %` hacen falta ~83 intentos y el presupuesto de 100 se queda corto.

---

## 🛠️ Las mitigaciones

Una **mitigación** es un mecanismo que se activa cuando el algoritmo se queda
sin salida, para empujarlo fuera del máximo local **sin cambiar el problema**.

| Mecanismo | Qué hace | Resultado medido |
|---|---|---|
| **Ninguna** | algoritmo puro | 48 % — el atasco |
| **Laterales (L)** | acepta pasos con `Δf = 0`, hasta `L` veces | no ayuda aquí: no hay mesetas. Con penalización sí se activa (17 862 veces) pero multiplica el trabajo ×12 |
| **Penalización (λ)** | hunde `f′` del estado estancado | escapa en 65 iteraciones; éxito 100 %; ~6× más lento |
| **Reinicios** | otro punto de partida al azar | éxito 100 %; 1,14 reinicios de media |

El límite `L` es imprescindible: sin él, el algoritmo podría vagar por una
meseta indefinidamente.

---

## 🎛️ Los controles

| Control | Para qué sirve |
|---|---|
| **Mapa** | A (control), B (trampa) o personalizado, editable con clics |
| **Variante** | `simple` (primer mejora) · `steepest` (mayor mejora) · `stochastic` (aleatorio ∝ Δf) · `first_choice` (barajado) |
| **Métrica** | `Manhattan` (enteros) o `Euclídea` (decimales) |
| **Vecindad** | `4` (cardinales) o `8` (+ diagonales sin cortar esquinas) |
| **Desempate** | `fijo` (reproducible) o `aleatorio` entre empatados |
| **Semilla** | hace reproducible la aleatoriedad: misma semilla → misma ejecución |
| **Mitigación** | ninguna · laterales con `L` · penalización con `λ` · reinicios con máximo |
| **Velocidad** | velocidad del modo automático |
| **Pasos** | `Paso` · `Auto/Pausa` · `Ejecutar hasta el final` · `Reiniciar` · `Exportar PNG` · `Guardar registro` |

---

## 🚀 Instalación y uso

Necesitas **Python 3.10 o superior**, `Pillow` y `pytest`.

```bash
# Windows (si el alias "python" no está disponible, usar "py")
py -m pip install -r requirements.txt

# Linux / macOS
python3 -m pip install -r requirements.txt

# Linux: la interfaz gráfica necesita Tk instalado por el sistema
#   Debian/Ubuntu:  sudo apt install python3-tk
#   Fedora:         sudo dnf install python3-tkinter
```

En Windows puedes abrir la demostración con **doble clic en `abrir_demo.bat`**.

| Qué quieres hacer | Comando |
|---|---|
| **Abrir la interfaz gráfica** | `py run_gui.py` |
| Demostración en consola, paso a paso | `py -m hillclimb.cli --mapa B --variante steepest --paso` |
| Ejecutar las pruebas | `py -m pytest -q` |
| Generar métricas y tablas | `py -m hillclimb.benchmark` |
| Repetir todo con métrica Euclídea | `py -m hillclimb.benchmark --metrica euclidea` |
| Generar las figuras del reporte | `py make_figures.py` |
| Regenerar las capturas de este README | `py tools/capturas.py` |
| Verificar las cifras (2.ª implementación) | `py tools/verificacion_independiente.py --mapa A B` |
| Análisis de escalabilidad | `py -m hillclimb.escalabilidad` |

Opciones de la CLI: `--metrica`, `--vecindad`, `--desempate`, `--laterales`,
`--penalizacion`, `--reinicios`, `--semilla`, `--max-iter`, `--auto`.

---

## 🏗️ Arquitectura

```
hill-climbing-lab/
├── README.md
├── requirements.txt
├── run_gui.py                  # lanza la interfaz gráfica
├── abrir_demo.bat              # doble clic en Windows
├── make_figures.py             # genera las 5 figuras del reporte
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
├── docs/modelado.md            # sección formal (notación S, N(s), f(s), Δf, p, B(s*))
├── docs/imagenes/              # capturas publicadas de la demostración
└── results/                    # metricas.csv, tablas, figuras/, entorno.md, log.txt
```

**Decisión de diseño clave:** cada ejecución es un **generador** que produce un
objeto de telemetría por iteración. La GUI y la CLI consumen el mismo generador
con `next()`, así que el modo paso a paso **no duplica código** y la lógica del
algoritmo no vive en la interfaz.

---

## ✅ Reproducibilidad y verificación

- **Determinismo.** Dos ejecuciones del benchmark producen el **mismo CSV salvo
  las columnas de tiempo**. Semillas derivadas de una sola maestra (42).
- **Verificación independiente.** `tools/verificacion_independiente.py`
  reimplementa *steepest*, las cuencas y A\* **sin importar nada del paquete**, y
  contrasta las cifras publicadas: coincidencia confirmada en `p`, número de
  celdas libres y longitud del camino de A\*.
- **Estadísticos robustos.** Mediana e IQR sobre 5 repeticiones con
  calentamiento, en vez de la media (sensible a valores atípicos).
- **Coste de la telemetría medido.** `hill_climbing_ligero` resuelve el mismo
  problema sin construir objetos de telemetría, para cuantificar su coste
  (`results/tiempo_telemetria.md`).
- **Entorno documentado.** `results/entorno.md` registra la versión de Python y
  los datos del equipo donde se tomaron las medidas.
- **Calidad del código.** 45 pruebas con `pytest`; `pyflakes` y `mypy` sin
  hallazgos; tipos y documentación en español.

---

## 🎤 Guion de presentación (4 personas, ~15 min)

La exposición cuenta tres actos. Este orden funciona mejor que empezar por el
fracaso: sin contexto, el atasco parece un bug.

### Reparto

| Persona | Acto | Contenido |
|---|---|---|
| **1** | El reto | problema, modelado, por qué es difícil |
| **2** | La herramienta | el algoritmo y la demo del Caso A |
| **3** | El fracaso | el atasco del Caso B y sus números |
| **4** | La solución | mitigaciones, métricas y cierre |

### Persona 1 — El problema y el modelo (3 min)

> *"Imaginen un laberinto de 7×9 con muros. Un agente sale de S y quiere llegar
> a G. El mapa B tiene una trampa: un recinto en U que se abre hacia el lado
> contrario de la meta."*

Tres ideas, y solo tres: **estado** = una celda `(fila, columna)`;
**vecindario** = las celdas contiguas en orden fijo `↑ ↓ ← →`; **aptitud**
`f(s) = −d(s, g)`, de modo que subir `f` es acercarse a `G`. El óptimo global
es la meta, con `f(g) = 0`.

*Transición:* «Ese paisaje se recorre con un algoritmo muy simple y muy miope:
Hill Climbing.»

### Persona 2 — El algoritmo y el Caso A (4 min)

La analogía de la montaña con niebla. El bucle en 4 líneas. Qué **no** hace: no
recuerda, no planifica, no retrocede, memoria O(1).

**Demo en vivo:** mapa A, steepest, sin mitigación. Pulsa **Paso** 3-4 veces
para que se vean los `Δf` verdes, luego **Ejecutar hasta el final**: llega a la
meta en **14 movimientos**, y desde cualquiera de las 58 celdas libres también.

*Transición:* «Pero el mapa A es el caso fácil. Cambiemos a un mapa con una
trampa.»

### Persona 3 — El atasco (4 min) ← el clímax

**Demo:** mapa B, **Reiniciar**, **Paso** una vez (va a (3,5)), **Paso** otra
(se detiene).

> *"Estado (3, 5), f = −3,00. Miren los tres vecinos: ↑ (2, 5), ↓ (4, 5),
> ← (3, 4). Todos con Δf = −1,00. Ninguno sube. Se declara máximo local y para.
> La meta está a tres pasos en línea recta, pero hay un muro. Para llegar habría
> que alejarse primero —bajar f— y este algoritmo nunca acepta bajar. No es un
> bug: es la naturaleza de la búsqueda local."*

Los números duros: `p = 24/50 = 48 %`, estancamiento del **52 %**, las 26
celdas atrapadas en el mismo sumidero, **barrera de 7,00**. Y el matiz fino:
las mesetas se midieron y **no aparecen** (verificado en 8 mapas y 2 métricas),
porque toda celda con lateral tiene también ascendente.

*Transición:* «¿Sirve un algoritmo que falla el 52 % de las veces? Sí, si sabes
sacarlo del atasco. Y hay tres formas.»

### Persona 4 — Mitigaciones, métricas y cierre (4 min)

**Demo 1 — Penalización:** λ = 1 → escapa, 65 iteraciones desde `S`, 100 % de
acierto.
**Demo 2 — Reinicios:** semilla 2024 → meta en 2 reinicios.
**Demo 3 — Laterales, con honestidad:** no se activan solos porque no hay
mesetas; con penalización sí, y encarece la búsqueda de 65 a 798 iteraciones.

Abrir `results/tabla_metricas.md`. Cierra con las tres ideas:

> *"Primero: la búsqueda local es muy barata —memoria constante, décimas de
> milisegundo— pero esa sencillez se paga con la posibilidad de atasco. Segundo:
> el atasco no se arregla con más potencia de cálculo, sino con mecanismos:
> penalizar lo visitado o reiniciar. Y tercero: un resultado no es un número, es
> un número más su intervalo de confianza y las condiciones bajo las que se
> midió."*

### Preguntas probables

| Pregunta | Respuesta en 15 segundos |
|---|---|
| ¿Por qué no A* directamente? | Garantiza el óptimo pero gasta memoria proporcional al espacio explorado; Hill Climbing gasta O(1). Es un intercambio explícito. |
| ¿Y si el mapa no tiene solución? | Los reinicios se agotan y el programa lo declara con `max_reinicios`, sin colgarse. Hay una prueba que lo verifica. |
| ¿Los números son fiables? | Deterministas salvo los tiempos, y hay una segunda implementación independiente que recalcula todo sin reusar el código. |
| ¿Qué es λ? | La intensidad de la penalización: con 1 basta; con 0.01 casi no penaliza. |
| ¿Por qué Euclídea si Manhattan es más natural? | Para medir si la métrica cambia el paisaje. Y sí: 48 % frente a 56 %. |

### Errores que arruinarían la exposición

1. **Empezar por el atasco.** Sin contexto parece un bug.
2. **Dejar la métrica en Euclídea para la demo principal.** Los `Δf` salen con
   decimales y el público se distrae; Manhattan da `−1,00`, limpio.
3. **No declarar la regla de desempate.** Si alguien replica con otro orden y le
   sale 56 % en vez de 48 %, parece un error. Dídelo tú primero.

---

## 📚 Conclusiones

1. **La búsqueda local es un intercambio, no una versión peor de A\*.** Memoria
   constante y coste ínfimo a cambio de no garantizar el óptimo. Elegir una u
   otra es una decisión de diseño que este trabajo hace explícita y medible.
2. **El atasco es predecible, no aleatorio.** `p = |B(g)|/|F|` y la profundidad
   de barrera cuantifican exactamente cuánto falla el algoritmo y por qué.
3. **Las mitigaciones tienen coste, y ese coste se mide.** La penalización
   resuelve el 100 % pero es ~6× más lenta; los laterales no sirven aquí y, cuando
   se activan, multiplican el trabajo por 12.
4. **Un resultado no es un número.** Es el número, su intervalo de confianza, la
   regla de desempate, la métrica y la vecindad con las que se obtuvo. Este
   repositorio declara todas esas condiciones en cada cifra que publica.
5. **Verificar con una implementación independiente encuentra lo que el ojo no
   ve.** La segunda implementación confirmó las cifras; los controles automáticos
   de las capturas encontraron dos defectos reales que una inspección visual
   había dado por buenas.

---

*Trabajo académico de la asignatura Fundamentos de Inteligencia Artificial /
Algoritmos de Optimización. Todas las cifras de este documento provienen de
`results/`, que se regenera con `python -m hillclimb.benchmark`.*
