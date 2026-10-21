# Análisis de resultados — Hill Climbing sobre laberinto con trampas cóncavas

Documento generado automáticamente por `python -m hillclimb.benchmark` (métrica Manhattan; semilla 42; 1000 ejecuciones por configuración aleatoria, exhaustivas en las deterministas, 5 repeticiones cronometradas por configuración). Todas las cifras son mediciones de esta ejecución; ninguna está precocinada. Entorno de medición: `entorno.md`.

## 1. Tabla de métricas

| Mapa | Métrica | Configuración | Ejecuciones | Tasa de éxito (%) | Estancamiento (%) | Iteraciones medias (éxito) | Iteraciones medias (fallo) | Reinicios medios | Tiempo mediana (ms) | Tiempo IQR (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Manhattan | HC simple (primer mejora) | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0556 | 0.0020 |
| A | Manhattan | HC steepest (ascenso más pronunciado) | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0571 | 0.0020 |
| A | Manhattan | HC estocástico (∝ Δf) | 1000 | 100.00 | 0.00 | 7.89 | — | 0.00 | 0.0626 | 0.0011 |
| A | Manhattan | HC first-choice (aleatorio) | 1000 | 100.00 | 0.00 | 7.89 | — | 0.00 | 0.0646 | 0.0040 |
| A | Manhattan | Steepest + laterales L=20 | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0568 | 0.0007 |
| A | Manhattan | Steepest + penalización λ=1 | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0573 | 0.0012 |
| A | Manhattan | Steepest + reinicios aleatorios (máx 100) | 1000 | 100.00 | 0.00 | 7.89 | — | 0.00 | 0.0657 | 0.0005 |
| B | Manhattan | HC simple (primer mejora) | 50 | 48.00 | 52.00 | 5.21 | 5.35 | 0.00 | 0.0395 | 0.0002 |
| B | Manhattan | HC steepest (ascenso más pronunciado) | 50 | 48.00 | 52.00 | 5.21 | 5.35 | 0.00 | 0.0420 | 0.0003 |
| B | Manhattan | HC estocástico (∝ Δf) | 1000 | 49.60 | 50.40 | 5.57 | 5.22 | 0.00 | 0.0460 | 0.0004 |
| B | Manhattan | HC first-choice (aleatorio) | 1000 | 50.90 | 49.10 | 5.71 | 5.14 | 0.00 | 0.0454 | 0.0003 |
| B | Manhattan | Steepest + laterales L=20 | 50 | 48.00 | 52.00 | 5.21 | 5.35 | 0.00 | 0.0426 | 0.0011 |
| B | Manhattan | Steepest + penalización λ=1 | 50 | 100.00 | 0.00 | 38.04 | — | 0.00 | 0.2671 | 0.0044 |
| B | Manhattan | Steepest + reinicios aleatorios (máx 100) | 1000 | 100.00 | 0.00 | 11.34 | — | 1.14 | 0.0940 | 0.0000 |


## 2. Dependencia del resultado respecto al desempate

`p` depende de cómo se resuelvan los empates. En el mapa B con métrica Manhattan, las 24 permutaciones del orden de exploración dan p entre **48.00 %** y **56.00 %** (media 52.00 %, desviación típica 3.27); con desempate aleatorio, entre **48.00 %** y **56.00 %** (media 50.30 %). Detalle completo, permutación por permutación, en `sensibilidad_desempate.md`.

**Regla usada por defecto en todo el repositorio:** orden fijo `↑ ↓ ← →` y, ante empates, el **primero** de los empatados (desempate estable y determinista). Todas las cifras de este documento usan esa regla.

## 3. Caso A: convergencia exitosa

El mapa A no contiene trampas cóncavas, de modo que la cuenca de atracción de la meta es todo el espacio libre: p = |B(g)|/|F| = 58/58 = 100.00 % y el estancamiento es 0.00 %. Steepest-Ascent desde S = (0, 0) llega a G = (6, 8) en 14 movimientos, que es exactamente la distancia de Manhattan entre ambos; el óptimo global f(g) = 0 se alcanza por un camino monótono ascendente. Las cuatro variantes y las tres mitigaciones aciertan todas desde todas las celdas: en el Caso A el paisaje no ofrece ninguna decisión peligrosa.

## 4. Caso B: atrapamiento en el máximo local (3, 5)

En el mapa B, Steepest-Ascent desde S = (3, 4) hace un único movimiento hasta (3, 5), donde f = -3.00 y los tres vecinos libres —(2, 5), (4, 5) y (3, 4)— tienen f = -4.00, es decir Δf = -1.00 en los tres: es un máximo local. La cuenca de atracción de la meta mide p = 24/50 = 48.00 %, de modo que el estancamiento es 52.00 % de las celdas libres. Las celdas atrapadas caen todas en el mismo sumidero (3, 5) (26 de 50 celdas); la profundidad de barrera de ese máximo local es d = 7.00, porque el único camino de escape pasa por (0, 1) o (6, 1), ambas con f = -10.00.

## 5. Métrica euclídea frente a Manhattan

Ambas métricas se miden siempre (cálculo exhaustivo desde cada celda libre), para que la comparación no dependa de con cuál se lanzó el benchmark. En el mapa B:

| Métrica | p = \|B(g)\|/\|F\| | Estancamiento | Sumideros |
|---|---|---|---|
| Manhattan | 48.00 % (24/50) | 52.00 % | 1 |
| Euclídea | 56.00 % (28/50) | 44.00 % | 1 |

La diferencia (56.00 % frente a 48.00 %) no es un error: `f(s) = -d(s, g)` cambia con la métrica y, con los empates resueltos por orden fijo, la elección entre vecinos también. Las dos métricas coinciden en lo estructural: el mapa B tiene un único sumidero, `(3, 5)`, que concentra todas las celdas atrapadas (26 de 50 con Manhattan).

En esta ejecución (métrica Manhattan), la penalización λ = 1 necesita **38.04 iteraciones** de media por celda libre (**38.04** según la tabla de arriba, que promedia solo los éxitos de la configuración medida) frente a las **63.60** que necesita con la otra métrica. La métrica euclídea produce valores de `f` con decimales, y al penalizar los empates y casi-empates se resuelven por caminos más largos.

## 6. La variante simple frente a la trampa

La variante *simple* (primer vecino que mejora en el orden fijo ↑ ↓ ← →) explora el mismo paisaje que *steepest*: en el mapa A su tasa de éxito es 100.00 % (58 ejecuciones exhaustivas, 7.97 iteraciones de media por éxito) y en el mapa B 48.00 % (5.35 iteraciones de media por fallo). Elegir el primer ascenso disponible en lugar del más pronunciado cambia el camino recorrido, pero no la topología del paisaje: ambas variantes caen en el mismo máximo local porque la trampa es una propiedad del mapa, no de la regla de avance.

## 7. Mitigación por penalización f′(s) = f(s) − λ·n(s)

Con λ = 1 y suficiente presupuesto de iteraciones, el algoritmo escapa de la trampa desde S: estado final «goal» tras 65 iteraciones (34 movimientos y 30 penalizaciones acumuladas sobre los estados estancados). Cada estancamiento aumenta n(s) y desplaza f′(s) hacia abajo, de modo que los vecinos antes inútiles se vuelven atractivos. Si se combina con laterales L = 20, el escape sigue produciéndose (goal en 798 iteraciones), con 687 movimientos laterales ejecutados sobre Δf = 0 que la propia penalización crea; el camino es mucho más largo, lo que muestra que los laterales solos no sirven aquí, pero tampoco estorban cuando hay penalización.

## 8. Mitigación por reinicios aleatorios frente a la teoría

**Definiciones.** Sea `K` el número de intentos (ejecuciones) hasta el primer éxito y `R = K − 1` el número de reinicios. El experimento muestrea la primera celda inicial de forma uniforme sobre las 50 celdas libres, así que cada intento acierta con probabilidad `p = 48.00 %` de forma independiente. Entonces:

- E[K] = 1/p = **2.08** ejecuciones totales.
- E[R] = (1 − p)/p = **1.08** reinicios (primer intento aleatorio).
- Si el primer intento partiese de `S`, que está dentro de la trampa, el primer fallo sería seguro y E[R] = 1/p = **2.08**.
- Medido sobre 1000 ejecuciones con éxito: **1.14** reinicios de media, con intervalo de confianza del 95 % por bootstrap [1.04, 1.25] reinicios (5000 remuestreos).

El valor teórico E[R] = (1 - p)/p = 1.08 cae dentro del intervalo bootstrap, mientras que E[R] = 1/p = 2.08 solo correspondería a un primer intento que partiese siempre de `S` (fallo seguro en el mapa B).

| Intentos permitidos r | 1 - (1 - p)^r teórico | Empírico: éxito en ≤ r intentos |
|---|---|---|
| 1 | 48.00 % | 46.80 % |
| 2 | 72.96 % | 72.40 % |
| 3 | 85.94 % | 85.40 % |
| 4 | 92.69 % | 91.90 % |
| 5 | 96.20 % | 95.50 % |

**Costo esperado.** Con t_f = 0.0400 ms (intento fallido) y t_s = 0.0298 ms (intento exitoso), medidos en el mismo experimento, el costo teórico `((1 − p)/p)·t_f + t_s` = **0.0732 ms**; la mediana medida por ejecución completa (todos sus intentos) es **0.0940 ms**.

Demostración manual con semilla fija 2024: desde S en el mapa B, los reinicios aleatorios alcanzan la meta («goal») usando 2 reinicio(s).

## 9. Movimientos laterales y mesetas

Con las métricas Manhattan y Euclídea en una vecindad de 4 direcciones, Δf nunca es exactamente 0: cualquier movimiento cambia la distancia a la meta en una cantidad distinta de cero, así que en estos mapas no existen mesetas y los movimientos laterales no se activan por sí solos (la configuración «Steepest + laterales L = 20» obtiene tasas de éxito idénticas a «Steepest»). El mecanismo queda implementado, limitado y a prueba de ciclos: no vuelve a la celda previa cuando existe alternativa, y cuando la penalización genera Δf = 0 sí se ejecuta (687 movimientos laterales en el experimento combinado).

**¿Y la vecindad de 8 direcciones?** La teoría sugiere que los movimientos en diagonal pueden dejar la distancia Manhattan invariante y con ello crear mesetas. Medido: con 8 direcciones sí existen celdas con algún vecino de `Δf = 0` (34 de 50 en el mapa B), pero **ninguna ejecución de las cuatro variantes termina en meseta**, en ninguno de los mapas ni en los aleatorios de `escalabilidad.md`. La razón es una propiedad verificada (`vecindad8.md`, sección 3): con la regla de *no cortar esquinas*, si una celda tiene vecino lateral entonces tiene también vecino ascendente, de modo que una meseta —sin ascendente pero con lateral— es inalcanzable. Los movimientos laterales solo resultan necesarios cuando otra mitigación crea empates.

## 10. Contraste de memoria con A*

Hill Climbing guarda un único estado (memoria O(1)). A*, con la misma heurística de Manhattan, expande 48 nodos y alcanza una frontera máxima de 7 celdas en el mapa B (camino de 16 movimientos); en el mapa A expande 58 nodos con frontera máxima 8 (camino de 14 movimientos).

## 11. Coste de la telemetría

El mismo trabajo resuelto sin construir los objetos `StepInfo` de la telemetría (`hill_climbing_ligero`) se recoge en `tiempo_telemetria.md`: la telemetría añade un factor aproximadamente constante por iteración, del orden de unas décimas de milisegundo por ejecución en mapas de 7 × 9. Es perfectamente asumible para la demo paso a paso y no debe usarse cuando solo se quieren métricas agregadas.

## 12. Eficiencia temporal

Mediana por ejecución del steepest en el mapa B: 0.0298 ms (éxito) y 0.0400 ms (fallo); mediana de toda la configuración exhaustiva en el mapa A: 0.0571 ms por ejecución. La búsqueda local es órdenes de magnitud más barata en tiempo, pero paga esa ventaja con la posibilidad de quedar atrapada.

## 13. Análisis adicionales

Este benchmark genera, además de los archivos anteriores:


- `sensibilidad_desempate.md` — `p` para las 24 permutaciones del orden de exploración y para 200 semillas con desempate aleatorio (sección 2 de este documento).
- `tiempo_telemetria.md` — coste de construir la telemetría frente al modo ligero `hill_climbing_ligero` (sección 11).
- `vecindad8.md` — vecindad de 8 direcciones: por qué no aparecen mesetas y cuándo sí se ejecutan los movimientos laterales (sección 9).
- `escalabilidad.md` y `figuras/p_vs_densidad.png` — mapas aleatorios de 15 × 15 y 25 × 25 con densidades de muro del 10 %, 20 % y 30 %.
- `entorno.md` — versión de Python y datos del equipo donde se tomaron las medidas. Los tiempos de este documento solo son comparables con los de la misma máquina.

Verificación independiente de las cifras principales (segunda implementación, sin reusar la lógica del paquete): `python tools/verificacion_independiente.py`.

