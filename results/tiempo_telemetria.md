# Coste de la telemetría paso a paso

Comparación del mismo trabajo resuelto con el generador telemetrado (`hill_climbing`, que construye un `StepInfo` por iteración) y con el modo ligero (`hill_climbing_ligero`, sin telemetría). 5 repeticiones, mediana e IQR por ejecución, mismo mapa y mismas semillas.

| Mapa | Métrica | Configuración | Ejecuciones | Mediana con telemetría (ms) | Mediana sin telemetría (ms) | Diferencia (veces) |
|---|---|---|---|---|---|---|
| B | Manhattan | HC simple (primer mejora) | 50 | 0.0395 | 0.0292 | 1.35 |
| B | Manhattan | HC steepest (ascenso más pronunciado) | 50 | 0.0420 | 0.0317 | 1.32 |
| B | Manhattan | HC estocástico (∝ Δf) | 1000 | 0.0460 | 0.0349 | 1.32 |
| B | Manhattan | HC first-choice (aleatorio) | 1000 | 0.0454 | 0.0344 | 1.32 |
| B | Manhattan | Steepest + laterales L=20 | 50 | 0.0426 | 0.0332 | 1.28 |
| B | Manhattan | Steepest + penalización λ=1 | 50 | 0.2671 | 0.1772 | 1.51 |
| B | Manhattan | Steepest + reinicios aleatorios (máx 100) | 1000 | 0.0940 | 0.0941 | 1.00 |

Los números son órdenes de magnitud de décimas de milisegundo en mapas de 7 × 9: la diferencia absoluta es minúscula, pero muestra que la telemetría cuesta un factor aproximadamente constante en trabajo por iteración, y que no debe activarse cuando solo interesan las métricas agregadas.

