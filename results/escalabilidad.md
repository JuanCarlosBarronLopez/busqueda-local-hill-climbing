# Escalabilidad: mapas aleatorios de 15 × 15 y 25 × 25

Mapas generados con semillas fijas a partir de 1000 y densidades de muro del 10 %, 20 % y 30 %. Los mapas sin solución (comprobado con BFS) se descartan y se regeneran. Las variantes aleatorias usan 200 intentos por mapa, con un máximo de 100 reinicios por ejecución.

| Tamaño | Densidad | Semilla | Libres | Muros | p Steepest 4 dir. | p Steepest 8 dir. | Mesetas 4 dir. | Mesetas 8 dir. | p reforicios | p penalización | Iter. Steepest | Iter. penalización |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15×15 | 10 % | 1000 | 208 | 17 | 59.13 % | 50.00 % | 0 | 0 | 100.00 % | 100.00 % | 11.00 | 19.65 |
| 15×15 | 20 % | 1001 | 180 | 45 | 3.89 % | 17.78 % | 0 | 0 | 98.50 % | 98.89 % | 6.88 | 37.22 |
| 15×15 | 30 % | 1002 | 160 | 65 | 6.88 % | 6.88 % | 0 | 0 | 100.00 % | 100.00 % | 6.17 | 77.42 |
| 25×25 | 10 % | 1003 | 567 | 58 | 24.87 % | 29.10 % | 0 | 0 | 100.00 % | 99.82 % | 15.20 | 33.81 |
| 25×25 | 20 % | 1004 | 502 | 123 | 1.20 % | 1.00 % | 0 | 0 | 72.00 % | 100.00 % | 14.22 | 95.70 |
| 25×25 | 30 % | 1005 | 442 | 183 | 2.49 % | 2.49 % | 0 | 0 | 92.00 % | 94.34 % | 7.21 | 271.23 |

**Mesetas terminales.** Con 4 direcciones: 0 en total, como predice el modelo (`Δf ≠ 0` para cualquier movimiento). Con 8 direcciones: 0. Es decir, **tampoco con 8 direcciones aparece ninguna meseta**, y la razón no es la geometría de estos mapas sino la regla de no cortar esquinas: toda celda con vecino lateral tiene también vecino ascendente (demostrado en `vecindad8.md`, sección 3).

**Conclusión.** Al aumentar la densidad de muros, `p` del Steepest cae de forma acentuada (del 59,13 % al 3,89 % en 15 × 15; del 24,87 % al 1,20 % en 25 × 25 entre el 10 % y el 20 % de muros), mientras que las dos mitigaciones mantienen tasas de éxito altas: la penalización λ = 1 acierta en el 98,89 %–100 % de los seis mapas y los reinicios aleatorios en el 72,00 %–100 %, con la única excepción del mapa 25 × 25 al 20 % (72,00 %), donde el presupuesto de 100 reinicios resulta insuficiente porque p ≈ 1,2 % implica E[K] ≈ 83 intentos. El coste por ejecución crece con el número de celdas pero se mantiene en milisegundos: la búsqueda local sigue siendo O(1) en memoria y muy barata en tiempo incluso a 25 × 25.

