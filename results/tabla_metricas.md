| Mapa | Métrica | Configuración | Ejecuciones | Tasa de éxito (%) | Estancamiento (%) | Iteraciones medias (éxito) | Iteraciones medias (fallo) | Reinicios medios | Tiempo mediana (ms) | Tiempo IQR (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Manhattan | HC simple (primer mejora) | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0581 | 0.0032 |
| A | Manhattan | HC steepest (ascenso más pronunciado) | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0628 | 0.0043 |
| A | Manhattan | HC estocástico (∝ Δf) | 1000 | 100.00 | 0.00 | 7.89 | — | 0.00 | 0.0716 | 0.0011 |
| A | Manhattan | HC first-choice (aleatorio) | 1000 | 100.00 | 0.00 | 7.89 | — | 0.00 | 0.0685 | 0.0017 |
| A | Manhattan | Steepest + laterales L=20 | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0641 | 0.0007 |
| A | Manhattan | Steepest + penalización λ=1 | 58 | 100.00 | 0.00 | 7.97 | — | 0.00 | 0.0656 | 0.0031 |
| A | Manhattan | Steepest + reinicios aleatorios (máx 100) | 1000 | 100.00 | 0.00 | 7.89 | — | 0.00 | 0.0743 | 0.0013 |
| B | Manhattan | HC simple (primer mejora) | 50 | 48.00 | 52.00 | 5.21 | 5.35 | 0.00 | 0.0427 | 0.0003 |
| B | Manhattan | HC steepest (ascenso más pronunciado) | 50 | 48.00 | 52.00 | 5.21 | 5.35 | 0.00 | 0.0456 | 0.0008 |
| B | Manhattan | HC estocástico (∝ Δf) | 1000 | 49.60 | 50.40 | 5.57 | 5.22 | 0.00 | 0.0518 | 0.0004 |
| B | Manhattan | HC first-choice (aleatorio) | 1000 | 50.90 | 49.10 | 5.71 | 5.14 | 0.00 | 0.0506 | 0.0010 |
| B | Manhattan | Steepest + laterales L=20 | 50 | 48.00 | 52.00 | 5.21 | 5.35 | 0.00 | 0.0461 | 0.0012 |
| B | Manhattan | Steepest + penalización λ=1 | 50 | 100.00 | 0.00 | 38.04 | — | 0.00 | 0.3009 | 0.0271 |
| B | Manhattan | Steepest + reinicios aleatorios (máx 100) | 1000 | 100.00 | 0.00 | 11.34 | — | 1.14 | 0.1042 | 0.0024 |
