import numpy as np
import pandas as pd

def generate_normal_data(n=200, mu=100, sigma=5):
    timestamps = pd.date_range("2026-01-01", periods=n, freq="h")
    values = np.random.normal(mu, sigma, n)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "value": values
    })
    return df

def add_mean_shift(df, shift=15, start_index=120):
    df = df.copy() 
    df.loc[start_index:, "value"] += shift
    return df

def add_variance_increase(df, extra_sigma=10, start_index=120):
    df = df.copy() 
    n = len(df) - start_index
    noise = np.random.normal(0, extra_sigma, n)
    df.loc[start_index:, "value"] += noise
    return df

# def add_missing_values(df, missing_ratio=0.2, start_index=120):
#     df = df.copy() 
#     n = len(df) - start_index
#     missing_indices = np.random.choice(
#         df.index[start_index:],
#         int(n * missing_ratio),
#         replace=False
#     )
#     df.loc[missing_indices, "value"] = np.nan
#     return df

def add_missing_values(df: pd.DataFrame, missing_ratio: float, start_index: int = 0) -> pd.DataFrame:
    """Добавляет пропуски в значения с заданной вероятностью после start_index"""
    df = df.copy()
    
    n = len(df)
    available_indices = df.index[start_index:]
    n_available = len(available_indices)
    n_missing = int(n_available * missing_ratio)  # Исправлено: от доступных строк
    
    # Защита от ошибки выборки
    n_to_sample = min(n_missing, n_available)
    if n_to_sample > 0:
        missing_indices = np.random.choice(
            available_indices,
            n_to_sample,
            replace=False
        )
        df.loc[missing_indices, 'value'] = np.nan
    else:
        print(f"Предупреждение: пропуски не добавлены (n_missing={n_missing}, n_available={n_available})")
    
    return df

def add_gradual_drift(df, drift_per_step=0.5, start_index=120):
    """Линейный дрейф среднего — каждая запись смещается на drift_per_step."""
    df = df.copy()
    for i, idx in enumerate(df.index[start_index:]):
        df.loc[idx, "value"] += drift_per_step * (i + 1)
    return df

def add_spikes(df, spike_prob=0.1, spike_magnitude=30, start_index=120):
    """Случайные выбросы с вероятностью spike_prob начиная с start_index."""
    df   = df.copy()
    mask = np.random.random(len(df) - start_index) < spike_prob
    signs = np.random.choice([-1, 1], size=mask.sum())
    df.loc[df.index[start_index:][mask], "value"] += signs * spike_magnitude
    return df


# Универсальная функция — используется из 4_experiment.py
DEGRADATION_FUNCS = {
    "none":          lambda df, start, val: df,
    "mean_shift":    lambda df, start, val: add_mean_shift(df, val, start),
    "variance":      lambda df, start, val: add_variance_increase(df, val, start),
    "missing":       lambda df, start, val: add_missing_values(df, val, start),
    "gradual_drift": lambda df, start, val: add_gradual_drift(df, val, start),
    "spikes":        lambda df, start, val: add_spikes(df, val, start),
}

def generate_data(n, mu, sigma, degradation, deg_start, deg_value):
    df   = generate_normal_data(n, mu, sigma)
    func = DEGRADATION_FUNCS.get(degradation, DEGRADATION_FUNCS["none"])
    return func(df, deg_start, deg_value)