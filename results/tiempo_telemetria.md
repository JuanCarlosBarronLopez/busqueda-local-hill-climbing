# Coste de la telemetría paso a paso

Comparación del mismo trabajo resuelto con el generador telemetrado (`hill_climbing`, que construye un `StepInfo` por iteración) y con el modo ligero (`hill_climbing_ligero`, sin telemetría). 5 repeticiones, mediana e IQR por ejecución, mismo mapa y mismas semillas.

| Mapa | Métrica | Configuración | Ejecuciones | Mediana con telemetría (ms) | Mediana sin telemetría (ms) | Diferencia (veces) |
|---|---|---|---|---|---|---|
| B | Manhattan | HC simple (primer mejora) | 50 | 0.0427 | 0.0331 | 1.29 |
| B | Manhattan | HC steepest (ascenso más pronunciado) | 50 | 0.0456 | 0.0365 | 1.25 |
| B | Manhattan | HC estocástico (∝ Δf) | 1000 | 0.0518 | 0.0399 | 1.30 |
| B | Manhattan | HC first-choice (aleatorio) | 1000 | 0.0506 | 0.0459 | 1.10 |
| B | Manhattan | Steepest + laterales L=20 | 50 | 0.0461 | 0.0362 | 1.27 |
| B | Manhattan | Steepest + penalización λ=1 | 50 | 0.3009 | 0.1986 | 1.51 |
| B | Manhattan | Steepest + reinicios aleatorios (máx 100) | 1000 | 0.1042 | 0.1168 | 0.89 |

Los números son órdenes de magnitud de décimas de milisegundo en mapas de 7 × 9: la diferencia absoluta es minúscula, pero muestra que la telemetría cuesta un factor aproximadamente constante en trabajo por iteración, y que no debe activarse cuando solo interesan las métricas agregadas.

