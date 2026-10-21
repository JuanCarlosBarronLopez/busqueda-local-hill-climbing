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
