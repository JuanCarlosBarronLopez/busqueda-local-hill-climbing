# Sensibilidad del resultado a la regla de desempate (mapa B)

La variante *steepest* debe elegir entre varios vecinos cuando empatan en `Δf`. Este documento mide cómo cambia `p = |B(g)|/|F|` según la regla de desempate, sobre el mapa B con métrica **Manhattan**.

- Celdas libres |F|: **50**.
- Orden fijo por defecto `↑ ↓ ← →`: **p = 48.00 %**.

## (a) Las 24 permutaciones del orden de movimientos

| Orden de exploración | p (%) |
|---|---|
| ↑↓←→ | 48.00 |
| ↑↓→← | 48.00 |
| ↑←↓→ | 48.00 |
| ↑←→↓ | 52.00 |
| ↑→↓← | 52.00 |
| ↑→←↓ | 52.00 |
| ↓↑←→ | 48.00 |
| ↓↑→← | 48.00 |
| ↓←↑→ | 48.00 |
| ↓←→↑ | 52.00 |
| ↓→↑← | 52.00 |
| ↓→←↑ | 52.00 |
| ←↑↓→ | 48.00 |
| ←↑→↓ | 52.00 |
| ←↓↑→ | 48.00 |
| ←↓→↑ | 52.00 |
| ←→↑↓ | 56.00 |
| ←→↓↑ | 56.00 |
| →↑↓← | 56.00 |
| →↑←↓ | 56.00 |
| →↓↑← | 56.00 |
| →↓←↑ | 56.00 |
| →←↑↓ | 56.00 |
| →←↓↑ | 56.00 |

**Mínimo 48.00 % · máximo 56.00 % · media 52.00 % · desviación típica 3.27 puntos porcentuales.**

## (b) Desempate aleatorio entre los empatados


200 semillas, cada una explorando las 50 celdas libres con un generador propio:


**Mínimo 48.00 % · máximo 56.00 % · media 50.30 % · desviación típica 1.98 puntos porcentuales.**

**Conclusión:** `p` no es una constante del mapa, sino del par (mapa, regla de desempate): en el mapa B oscila entre 48.00 % y 56.00 % según cómo se resuelvan los empates. El resto del repositorio fija el desempate **por orden canónico `↑ ↓ ← →`, tomando el primero de los empatados**, que es la opción determinista y reproducible.

