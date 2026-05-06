"""
Конфигурации экспериментальных серий.

ВАЖНО про масштаб:
    SPC применяется к МЕТРИКАМ ОКОН (среднее по окну размера w), а не к сырым
    данным. По центральной предельной теореме, для метрики "среднее по окну":
        σ_window = σ_raw / √w

    При DEFAULT_SIGMA_RAW = 5.0 и DEFAULT_WINDOW_SIZE = 20:
        σ_window = 5.0 / √20 ≈ 1.118

    Все величины сдвига в сериях 2-4 задаются в единицах σ_window и
    конвертируются в абсолютные единицы для генератора.
"""

import math


# ── Общие константы ──────────────────────────────────────────────────────
DEFAULT_BASELINE_SIZE   = 50
DEFAULT_WINDOW_SIZE     = 20
DEFAULT_MU              = 100.0
DEFAULT_SIGMA_RAW       = 5.0
DEFAULT_SIGMA_WINDOW    = DEFAULT_SIGMA_RAW / math.sqrt(DEFAULT_WINDOW_SIZE)  # ≈ 1.118
DEFAULT_REPLICATIONS    = 30


# ═══════════════════════════════════════════════════════════════════════════
# СЕРИЯ 1: Валидация ARL₀
# ═══════════════════════════════════════════════════════════════════════════
SERIES_1_ARL0 = {
    "name": "series1_arl0",
    "description": "Валидация ARL₀ — частота ложных срабатываний на чистом ряду",
    "scenarios": [
        {
            "name":           "clean_baseline",
            "n_observations": 31000,    # 50 окон baseline + 1500 окон фазы II
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "none",
            "deg_value":      0,
            "deg_start":      None,
            "metric":         "mean",
        },
    ],
    "replications": DEFAULT_REPLICATIONS,
    "baseline_size": DEFAULT_BASELINE_SIZE,
}


# ═══════════════════════════════════════════════════════════════════════════
# СЕРИЯ 2: Чувствительность к величине сдвига (валидация ARL₁)
# ═══════════════════════════════════════════════════════════════════════════
SERIES_2_ARL1 = {
    "name": "series2_arl1",
    "description": "Чувствительность к величине сдвига среднего",
    "scenarios": [
        {
            "name":           f"shift_{shift:.1f}sigma",
            "n_observations": 11000,
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "mean_shift",
            "deg_value":      shift * DEFAULT_SIGMA_WINDOW,
            "deg_start":      1000,
            "metric":         "mean",
        }
        for shift in [0.5, 1.0, 1.5, 2.0, 3.0]
    ],
    "replications": DEFAULT_REPLICATIONS,
    "baseline_size": DEFAULT_BASELINE_SIZE,
}


# ═══════════════════════════════════════════════════════════════════════════
# СЕРИЯ 3: Сравнение методов на разных типах деградации
#
# Сценарии дрейфа:
#   gradual_drift_fast — 0.05 σ_window/запись (за 5 окон накапливается 5σ_w)
#                         все методы быстро реагируют, разница не заметна
#   gradual_drift_slow — 0.005 σ_window/запись (в 10 раз медленнее)
#                         Шухарт может пропускать, CUSUM/EWMA обнаружат лучше
# ═══════════════════════════════════════════════════════════════════════════
SERIES_3_COMPARISON = {
    "name": "series3_comparison",
    "description": "Сравнение методов на разных типах деградации",
    "scenarios": [
        {
            "name":           "mean_shift_2sigma",
            "n_observations": 11000,
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "mean_shift",
            "deg_value":      2.0 * DEFAULT_SIGMA_WINDOW,
            "deg_start":      1000,
            "metric":         "mean",
        },
        {
            "name":           "gradual_drift_fast",
            "n_observations": 11000,
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "gradual_drift",
            "deg_value":      0.05 * DEFAULT_SIGMA_WINDOW,
            "deg_start":      1000,
            "metric":         "mean",
        },
        {
            "name":           "gradual_drift_slow",
            "n_observations": 11000,
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "gradual_drift",
            "deg_value":      0.005 * DEFAULT_SIGMA_WINDOW,
            "deg_start":      1000,
            "metric":         "mean",
        },
        {
            "name":           "variance_doubling",
            "n_observations": 11000,
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "variance",
            "deg_value":      DEFAULT_SIGMA_RAW,
            "deg_start":      1000,
            "metric":         "std",
        },
        {
            "name":           "spikes_5pct",
            "n_observations": 11000,
            "window_size":    DEFAULT_WINDOW_SIZE,
            "mu":             DEFAULT_MU,
            "sigma":          DEFAULT_SIGMA_RAW,
            "degradation":    "spikes",
            "deg_value":      0.05,
            "deg_start":      1000,
            "metric":         "mean",
        },
    ],
    "replications": DEFAULT_REPLICATIONS,
    "baseline_size": DEFAULT_BASELINE_SIZE,
}


# ═══════════════════════════════════════════════════════════════════════════
# СЕРИЯ 4: Границы применимости
# ═══════════════════════════════════════════════════════════════════════════
SERIES_4_BOUNDARIES = {
    "name": "series4_boundaries",
    "description": "Анализ границ применимости методов",
    "scenarios": [
        # 4а: разный baseline_size
        *[
            {
                "name":           f"baseline_{bs}",
                "n_observations": 20000 + bs * DEFAULT_WINDOW_SIZE,
                "window_size":    DEFAULT_WINDOW_SIZE,
                "mu":             DEFAULT_MU,
                "sigma":          DEFAULT_SIGMA_RAW,
                "degradation":    "none",
                "deg_value":      0,
                "deg_start":      None,
                "metric":         "mean",
                "baseline_size":  bs,
            }
            for bs in [20, 50, 100, 200]
        ],
        # 4б: разная доля выбросов
        *[
            {
                "name":           f"spikes_{int(p*100)}pct",
                "n_observations": 11000,
                "window_size":    DEFAULT_WINDOW_SIZE,
                "mu":             DEFAULT_MU,
                "sigma":          DEFAULT_SIGMA_RAW,
                "degradation":    "spikes",
                "deg_value":      p,
                "deg_start":      1000,
                "metric":         "mean",
            }
            for p in [0.05, 0.10, 0.20, 0.30]
        ],
    ],
    "replications": DEFAULT_REPLICATIONS,
    "baseline_size": DEFAULT_BASELINE_SIZE,
}


# ═══════════════════════════════════════════════════════════════════════════
# СЕРИЯ 5: Live-мониторинг (выполняется через UI)
# ═══════════════════════════════════════════════════════════════════════════
SERIES_5_LIVE = {
    "name": "series5_live",
    "description": "Демонстрация на реальных данных (выполняется в UI)",
    "scenarios": [],
    "replications": 0,
    "baseline_size": DEFAULT_BASELINE_SIZE,
    "note": "Запуск через UI live-мониторинг. Анализ по логу spc_event основной БД.",
}


ALL_SERIES = {
    "1": SERIES_1_ARL0,
    "2": SERIES_2_ARL1,
    "3": SERIES_3_COMPARISON,
    "4": SERIES_4_BOUNDARIES,
    "5": SERIES_5_LIVE,
}
