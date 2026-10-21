# 3. Modelado del problema implementado

> Sección lista para integrar al reporte técnico. Usa la notación
> `S`, `N(s)`, `f(s)`, `Δf`, `p`, `B(s*)` de forma consistente con el resto
> del documento y con el código del repositorio.

## 3.1 El problema: escapar de un laberinto con trampas cóncavas

El problema es el **escape de un laberinto con trampas cóncavas**: el buscador
parte de la celda inicial `S` y debe alcanzar la meta `G` en una cuadrícula
2D de 7 × 9 celdas donde algunas celdas son muros (`#`). El mapa **B**
contiene una trampa cóncava: un recinto en forma de **U** cuya abertura mira
en dirección contraria a la meta, de modo que el gradiente de la función de
aptitud conduce al fondo del recinto y lo deja sin salida. El mapa **A** es el
control: misma geometría de muros, pero sin trampa cóncava, por lo que no
existe ningún máximo local.

## 3.2 Definición formal

**Espacio de estados.** `F` es el conjunto de celdas libres del laberinto.
Un estado `s ∈ F` es una celda libre identificada por sus coordenadas
enteras `s = (r, c)`, con `r` la fila y `c` la columna. Se distinguen dos
estados particulares: el inicial `S = (r_S, c_S)` y la meta `g = (r_g, c_g)`.

**Función de aptitud (a maximizar).**

```
f(s) = −d(s, g)
```

donde `d` es una distancia entre celdas, seleccionable entre:

```
d_Manhattan(s, g) = |r − r_g| + |c − c_g|          (métrica por defecto)
d_Euclídea(s, g)  = √((r − r_g)² + (c − c_g)²)
```

El óptimo global es la meta: `f(g) = 0`. Como `f` decrece monótonamente con la
distancia, maximizar `f` equivale a minimizar la distancia a `G`, y **todo
aumento de `f` acerca al buscador a la meta**.

**Generación del vecindario.** `N(s)` contiene las celdas libres adyacentes en
las **cuatro direcciones cardinales, sin diagonales**:

```
N(s) = { (r±1, c), (r, c±1) ⊆ F }
```

Cada vecino se explora en un **orden FIJO `↑ ↓ ← →`**, y los muros quedan
excluidos de `N(s)`. El orden fijo hace que las variantes deterministas sean
reproducibles y que el desempate sea estable: cuando dos vecinos empatan en
`Δf`, gana el que aparece primero en ese orden (existe además un modo de
desempate aleatorio con semilla).

**Regla de avance y Δf.** Dado `s`, el algoritmo evalúa cada `s' ∈ N(s)` con
la función penalizada `f'` (apartado 3.4) y calcula

```
Δf(s, s') = f'(s') − f'(s)
```

Un movimiento es **ascendente** si `Δf > 0`. Las variantes implementadas son:

| Variante | Regla de selección entre los vecinos con `Δf > 0` |
|---|---|
| `simple` | el primero que mejora en el orden fijo `↑ ↓ ← →` |
| `steepest` | el de mayor `Δf` (ascenso más pronunciado; empate → orden fijo) |
| `stochastic` | elección probabilística con peso proporcional a `Δf` (con semilla) |
| `first_choice` | el primero que mejora tras barajar aleatoriamente el vecindario |

## 3.3 Condiciones de terminación

La ejecución se detiene en la primera iteración que cumpla una de estas
condiciones:

1. **Meta alcanzada**: `s = g`, con `f(s) = 0`.
2. **Máximo local**: ningún vecino con `Δf > 0` y ninguno con `Δf = 0`, es
   decir `∀ s' ∈ N(s): Δf(s, s') < 0`. El estado es un óptimo local
   estricto `f(s) < 0` que no es el global.
3. **Meseta**: ningún vecino con `Δf > 0` pero sí alguno con `Δf = 0` (el
   algoritmo podría seguir moviéndose sin mejorar; el límite de movimientos
   laterales decide si lo hace o si se declara atrapado).
4. **Límite de iteraciones**: se agota `max_iter`.

Con las métricas Manhattan y Euclídea `Δf` nunca es exactamente 0 (cualquier
movimiento cambia la distancia en una cantidad distinta de cero), por lo que
en este modelo **no aparecen mesetas de forma natural**: el caso 3 solo se
produce cuando la penalización del apartado 3.4 genera empates.

## 3.4 Función penalizada f′(s)

Para escapar de un estancamiento se penaliza el estado visitado:

```
f′(s) = f(s) − λ · n(s)
```

donde `n(s)` es el número de veces que el algoritmo se ha estancado en `s`
durante la ejecución actual y `λ ≥ 0` la intensidad de la penalización. Cada
estancamiento incrementa `n(s)`, hunde `f′(s)` y hace que los vecinos antes
inútiles resulten atractivos, forzando la salida del máximo local. La
telemetría muestra en cada iteración tanto `f` como los `Δf` calculados sobre
`f′`.

## 3.5 Estructura del paisaje y notación del análisis

Sea `B(s*)` la **cuenca de atracción** de un estado final `s*`: el conjunto de
estados iniciales desde los que la variante determinista elegida termina
exactamente en `s*`. Con ellas se definen:

```
p        = |B(g)| / |F|            probabilidad de éxito (celda inicial uniforme)
1 − p    = porcentaje de estancamiento
```

Para cuantificar la trampa se usa la **profundidad de barrera** de un máximo
local `s°`:

```
d(s°) = f(s°) − M
```

donde `M` es el máximo, sobre todos los caminos que parten de `s°` y llegan a
un estado mejor, del **mínimo** de `f` a lo largo del camino (búsqueda del
camino *maximín*). En el mapa B, el máximo local `(3, 5)` tiene
`f((3,5)) = −3` y `d = 7.00`, porque todo camino de escape pasa por `(0, 1)` o
`(6, 1)`, ambas con `f = −10`.

## 3.6 Admisibilidad de la heurística

Con la métrica Manhattan, `d(s, g)` es una heurística **admisible** para el
coste real de alcanzar `g`: nunca lo sobreestima, porque cada movimiento
cambia `|r − r_g| + |c − c_g|` como máximo en 1 y el camino más corto posible
mide exactamente `d(s, g)` aristas. Por eso `f(s) = −d(s, g)` orienta
correctamente la búsqueda local y, usada como heurística de A*, garantiza el
camino óptimo (contraste de memoria que mide el repositorio).

## 3.7 Mitigaciones del estancamiento

| Mecanismo | Formalización |
|---|---|
| Movimientos laterales con límite `L` | se acepta `s'` con `Δf = 0` mientras el contador de laterales sea `< L` (nunca se vuelve a la celda previa si hay alternativa) |
| Penalización | `f′(s) = f(s) − λ·n(s)` con `n(s)` creciente en cada estancamiento |
| Reinicios aleatorios | tras un fallo, `S ← s ∈ F` uniforme; reinicios esperados `1/p`, éxito tras `r` reinicios `1 − (1 − p)^r`, costo esperado `((1 − p)/p)·t_f + t_s` |

## 3.8 La regla de desempate forma parte del modelo

Cuando dos o más vecinos empatan en `Δf`, la elección entre ellos es una
decisión de diseño que **cambia el resultado medido**. En el mapa B, las 24
permutaciones posibles del orden de exploración dan valores de `p` entre el
48,00 % y el 56,00 %, y el desempate aleatorio entre 48,00 % y 56,00 %
(`results/sensibilidad_desempate.md`). Por eso este trabajo fija una regla
explícita y la declara en todos los resultados:

> **Regla por defecto:** orden fijo `↑ ↓ ← →` y, ante empates, el **primero**
> de los empatados (desempate estable y determinista).

El código permite alternativas (`hill_climbing(..., desempate="aleatorio")`,
`hill_climbing(..., orden=<permutación>)`, y la GUI expone ambas opciones),
pero ninguna cifra publicada las usa salvo en el experimento de sensibilidad.

## 3.9 ¿Existen mesetas? Un resultado negativo verificado

Con la métrica Manhattan o Euclídea y la vecindad de 4 direcciones, **nunca**
hay mesetas: cualquier movimiento cambia la distancia a la meta en una
cantidad distinta de cero, luego `Δf ≠ 0`.

Con la vecindad de 8 direcciones (diagonales añadidas, `--vecindad 8`) el
planteo habitual anuncia mesetas, porque un movimiento en diagonal puede
dejar invariante la suma `|r − r_g| + |c − c_g|`. **Medido: no ocurre.** La
razón es una propiedad que se verificó celda por celda en todos los mapas del
repositorio (A, B y los aleatorios de `results/escalabilidad.md`) **y con las
dos métricas, Manhattan y Euclídea**:

> Si una celda tiene algún vecino con `Δf = 0` y la regla es *no cortar
> esquinas*, entonces las dos celdas cardinales adyacentes existen libres y
> tienen `Δf > 0`. Luego «tener lateral» implica «tener ascendente», y una
> meseta (sin ascendente pero con lateral) es **inalcanzable**.

Consecuencia práctica: los movimientos laterales, implementados con límite
`L` y a prueba de ciclos, **no se activan por sí solos** en ningún mapa
medido. Sí se activan —y son necesarios— cuando otra mitigación genera
empates: con la penalización `f′` se ejecutan 17 862 de ellos en el mapa B
(`results/vecindad8.md`). Este es un resultado negativo verificado, no una
meseta fabricada: para observar mesetas terminales haría falta permitir
cortar esquinas, que no es el modelo de este trabajo.

## 3.10 Implementación y reproducibilidad

Cada ejecución es un **generador** que produce un objeto de telemetría por
iteración (estado actual, `f(actual)`, vecinos evaluados con `f(vecino)` y
`Δf`, celda elegida, razón de la decisión y estado final), de forma que el
modo paso a paso de la GUI y de la CLI consumen exactamente la misma fuente.
La reproducibilidad se apoya en tres decisiones: el orden fijo `↑ ↓ ← →`, el
desempate estable y las semillas explícitas (`42` en el benchmark, `2024` en
la demostración manual de reinicios). Todas las métricas del reporte se
generan ejecutando el benchmark, que mide tiempos con
`time.perf_counter_ns` usando **mediana y rango intercuartílico sobre 5
repeticiones** con calentamiento previo, y que es reproducible: dos
ejecuciones consecutivas producen el mismo CSV salvo las columnas de tiempo.

El mismo trabajo puede medirse sin telemetría
(`hill_climbing_ligero`), lo que cuantifica el coste de los objetos que
consume la GUI (`results/tiempo_telemetria.md`).
