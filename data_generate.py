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
    df.loc[start_index:, "value"] += shift
    return df

def add_variance_increase(df, extra_sigma=10, start_index=120):
    n = len(df) - start_index
    noise = np.random.normal(0, extra_sigma, n)
    df.loc[start_index:, "value"] += noise
    return df

def add_missing_values(df, missing_ratio=0.2, start_index=120):
    n = len(df) - start_index
    missing_indices = np.random.choice(
        df.index[start_index:],
        int(n * missing_ratio),
        replace=False
    )
    df.loc[missing_indices, "value"] = np.nan
    return df


df = generate_normal_data()
df = add_mean_shift(df, shift=20, start_index=120)
df.to_csv("source_c.csv", index=False)

df = generate_normal_data()
df = add_variance_increase(df)
df.to_csv("source_a.csv", index=False)

df = generate_normal_data()
df = add_missing_values(df)
df.to_csv("source_b.csv", index=False)