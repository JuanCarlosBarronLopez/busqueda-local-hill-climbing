# Propiedad verificada: «tener vecino lateral implica tener ascendente»

Comprobación exhaustiva, celda por celda, de la implicación que explica por qué **no aparecen mesetas** ni con la vecindad de 8 direcciones. Se verifica sobre todos los mapas del repositorio —A, B y los seis aleatorios de escalabilidad— y con las dos métricas.

| Mapa | Métrica | Celdas libres | Con vecino lateral | Con lateral y ascendente | Solo lateral |
|---|---|---|---|---|---|
| A | Manhattan | 58 | 48 | 48 | 0 |
| A | Euclídea | 58 | 2 | 2 | 0 |
| B | Manhattan | 50 | 34 | 34 | 0 |
| B | Euclídea | 50 | 3 | 3 | 0 |
| 15×15 al 10 % | Manhattan | 208 | 191 | 191 | 0 |
| 15×15 al 10 % | Euclídea | 208 | 18 | 18 | 0 |
| 15×15 al 20 % | Manhattan | 180 | 127 | 127 | 0 |
| 15×15 al 20 % | Euclídea | 180 | 8 | 8 | 0 |
| 15×15 al 30 % | Manhattan | 160 | 88 | 88 | 0 |
| 15×15 al 30 % | Euclídea | 160 | 8 | 8 | 0 |
| 25×25 al 10 % | Manhattan | 567 | 522 | 522 | 0 |
| 25×25 al 10 % | Euclídea | 567 | 36 | 36 | 0 |
| 25×25 al 20 % | Manhattan | 502 | 353 | 353 | 0 |
| 25×25 al 20 % | Euclídea | 502 | 20 | 20 | 0 |
| 25×25 al 30 % | Manhattan | 442 | 228 | 228 | 0 |
| 25×25 al 30 % | Euclídea | 442 | 8 | 8 | 0 |

- **Manhattan**: 1591 celdas con vecino lateral examinadas, **0** sin vecino ascendente.
- **Euclídea**: 103 celdas con vecino lateral examinadas, **0** sin vecino ascendente.

La implicación se cumple sin excepción en todos los mapas y con las dos métricas. Por tanto una meseta —estado sin vecino ascendente pero con alguno lateral— es **inalcanzable** bajo la regla de no cortar esquinas, y esa es la razón por la que el recuento de mesetas terminales es 0 en `vecindad8.md` y en `escalabilidad.md`.

Para observar mesetas terminales haría falta permitir **cortar esquinas**: un movimiento en diagonal cuyas dos celdas ortogonales son muro. No es el modelo de este trabajo.

