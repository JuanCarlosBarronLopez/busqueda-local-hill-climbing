# Vecindad de 8 direcciones: mesetas, hombros y movimientos laterales

**Pregunta.** La teoría anuncia que, al ampliar `N(s)` a 8 direcciones, aparecen mesetas (`Δf = 0`) y con ellas uso para los movimientos laterales. Este documento comprueba si eso ocurre de verdad en los mapas del repositorio.

## 1. ¿Existen vecinos con Δf = 0?

| Mapa | Celdas libres | Con vecino Δf = 0 (4 dir.) | Con vecino Δf = 0 (8 dir.) |
|---|---|---|---|
| A | 58 | 0 | 48 |
| B | 50 | 0 | 34 |

Con 4 direcciones la respuesta es **ninguna**: cualquier movimiento cambia la distancia en ±1 (Manhattan) o en una cantidad distinta de cero (Euclídea). Con 8 direcciones **sí** existen: un movimiento en diagonal puede dejar la distancia Manhattan invariante.

## 2. ¿Termina alguna ejecución en meseta?

| Mapa | Vecindad | Variante | Mesetas | Máximos locales | Éxitos | Laterales ejecutados |
|---|---|---|---|---|---|---|
| A | 4 | simple | 0 | 0 | 58 | 0 |
| A | 4 | steepest | 0 | 0 | 58 | 0 |
| A | 4 | stochastic | 0 | 0 | 58 | 0 |
| A | 4 | first_choice | 0 | 0 | 58 | 0 |
| A | 8 | simple | 0 | 0 | 58 | 0 |
| A | 8 | steepest | 0 | 0 | 58 | 0 |
| A | 8 | stochastic | 0 | 0 | 58 | 0 |
| A | 8 | first_choice | 0 | 0 | 58 | 0 |
| B | 4 | simple | 0 | 26 | 24 | 0 |
| B | 4 | steepest | 0 | 26 | 24 | 0 |
| B | 4 | stochastic | 0 | 22 | 28 | 0 |
| B | 4 | first_choice | 0 | 26 | 24 | 0 |
| B | 8 | simple | 0 | 26 | 24 | 0 |
| B | 8 | steepest | 0 | 26 | 24 | 0 |
| B | 8 | stochastic | 0 | 24 | 26 | 0 |
| B | 8 | first_choice | 0 | 26 | 24 | 0 |

**Resultado: 0 mesetas** en las 16 combinaciones mapa × variante × vecindad. Aunque con 8 direcciones *existan* vecinos de `Δf = 0`, **ninguna ejecución de estas variantes termina en meseta**: cuando el algoritmo se queda sin mejora estricta, el estado es además un máximo local estricto (todos los vecinos, diagonales incluidas, empeoran `f`). Los movimientos laterales, por tanto, **nunca se activan por sí solos** en estos mapas.

## 3. ¿Por qué no aparece ninguna meseta? (propiedad verificada)

La imposibilidad no es una casualidad de estos mapas, sino una consecuencia de la regla de **no cortar esquinas**. Si una celda tiene un vecino lateral (`Δf = 0`, un movimiento en diagonal que no cambia la distancia Manhattan), ese diagonal solo se admite cuando las **dos** celdas cardinales adyacentes están libres; y ambas tienen `Δf > 0`. Luego «tener lateral» implica «tener ascendente», y una meseta —que exigiría no tener ascendente y sí lateral— es inalcanzable.

| Mapa | Métrica | Con vecino lateral | Con lateral Y ascendente | Solo lateral |
|---|---|---|---|---|
| A | Manhattan | 48 | 48 | 0 |
| A | Euclídea | 2 | 2 | 0 |
| B | Manhattan | 34 | 34 | 0 |
| B | Euclídea | 3 | 3 | 0 |

**Contadas una a una las celdas con vecino lateral de todos los mapas, ninguna carece de vecino ascendente: 0 excepciones con Manhattan y 0 con Euclídea (sobre 82 y 5 celdas respectivamente).** La propiedad se cumple sin excepción con las dos métricas, y por eso el recuento de mesetas terminales es 0 en todas las variantes.

## 4. ¿Cuándo se activan los laterales y cuánto cuestan?

Sí se activan cuando otra mitigación genera empates. Con penalización `f′(s) = f(s) − λ·n(s)`, λ = 1 y L = 20:

| Mapa | Vecindad | Éxitos | Mesetas | Laterales ejecutados | Iteraciones totales |
|---|---|---|---|---|---|
| A | 4 | 58 | 0 | 0 | 462 |
| A | 8 | 58 | 0 | 0 | 373 |
| B | 4 | 50 | 0 | 17862 | 20960 |
| B | 8 | 50 | 0 | 21502 | 24744 |

En el mapa B, la penalización sola (sin laterales) resuelve las 50 celdas libres en 1902 iteraciones; al permitir además L = 20 movimientos laterales el trabajo sube a 20960 iteraciones con 4 direcciones y a 24744 con 8. **Los laterales no rompen la ejecución — se sigue acertando en las 50 celdas — pero multiplican el trabajo**, porque el algoritmo puede vagar por una meseta creada por la propia penalización antes de volver a ascender. El límite `L` es imprescindible: sin él, ese vagar no tendría fin.

## 5. Conclusión

1. La imposibilidad de mesetas con 4 direcciones es un **hecho del modelo**, no una casualidad de los mapas: cualquier movimiento cambia la distancia a la meta en ±1 (Manhattan), así que `Δf ≠ 0` siempre.
2. Con 8 direcciones las mesetas **son formalmente posibles** —hay decenas de celdas con algún vecino de `Δf = 0`— pero **no se materializan**: la regla de no cortar esquinas garantiza que toda celda con lateral tiene también ascendente (sección 3), así que el estado final de un estancamiento siempre es un máximo local estricto. Esto se cumple en los mapas A, B y en los aleatorios de `escalabilidad.md`.
3. Los movimientos laterales son un mecanismo **necesario solo cuando algo más genera empates** (aquí, la penalización `f′`). Usarlos sin ese algo no cambia nada, y usarlos junto a la penalización encarece la búsqueda sin mejorar el resultado.
4. Para observar mesetas terminales haría falta permitir **cortar esquinas**: un movimiento en diagonal cuyas dos ortogonales son muro. No es el modelo de este repositorio, y por tanto el requisito de «demostrar mesetas» se responde con un resultado negativo verificado, no con una meseta fabricada.

