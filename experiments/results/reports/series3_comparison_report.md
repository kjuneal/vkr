# Серия 3: Сравнение методов

## Сводная таблица

```
          scenario  CUSUM  EWMA  Шухарт
gradual_drift_fast    4.0   3.7     3.8
gradual_drift_slow   14.0  14.1    17.0
 mean_shift_2sigma    3.7   2.5     3.8
       spikes_5pct   27.8  17.9     7.4
 variance_doubling    3.3   2.3     3.0
```

## Сгенерированные файлы

- `series3_comparison_delay.csv` — Средние задержки
- `series3_comparison_rate.csv` — Доля прогонов с обнаружением
- `figures/series3_comparison_bars.png` — Сравнительный барчарт