import requests
from datetime import datetime

def compute_metrics(series, selected: list) -> dict:
    """
    Вычисляет выбранные метрики для pandas Series.
    series  — столбец значений (может содержать NaN)
    selected — список строк: ['mean','std','completeness','median','iqr']
    """
    results = {}
    n       = len(series)
    clean   = series.dropna()  # без NaN для числовых метрик

    if "mean" in selected:
        results["mean"] = float(clean.mean()) if len(clean) else float("nan")

    if "std" in selected:
        results["std"] = float(clean.std()) if len(clean) > 1 else 0.0

    if "completeness" in selected:
        results["completeness"] = float(1 - series.isna().sum() / n) if n else 0.0

    if "median" in selected:
        results["median"] = float(clean.median()) if len(clean) else float("nan")

    if "iqr" in selected:
        q75, q25 = clean.quantile(0.75), clean.quantile(0.25)
        results["iqr"] = float(q75 - q25) if len(clean) else float("nan")

    # count всегда добавляем — нужен для контекста
    results["count"] = n

    return results

class BaseAgent:

    def __init__(self, server_url):
        self.server_url = server_url

    def send_metrics(self, source_name, metrics):

        payload = {
            "source": source_name,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }

        response = requests.post(
            f"{self.server_url}/metrics/",
            json=payload
        )

        print("Payload:", payload)
        print("Server response:", response.status_code)
        print("Server message:", response.text)