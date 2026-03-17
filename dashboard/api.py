import requests
import streamlit as st

def reset_experiment():
    try:
        r = requests.delete(f"{API_URL}/reset/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

API_URL = "http://127.0.0.1:8000"

METRIC_LABELS = {
    "mean":         "Среднее",
    "std":          "Стд. отклонение",
    "completeness": "Полнота",
    "count":        "Количество",
    "missing_count":"Пропуски",
}

def metric_label(name: str) -> str:
    return METRIC_LABELS.get(name, name)

@st.cache_data(ttl=30)
def get_all_states():
    try:
        r = requests.get(f"{API_URL}/spc/", timeout=5)
        return r.json()
    except Exception:
        return []

@st.cache_data(ttl=30)
def get_state(source, metric_name):
    try:
        r = requests.get(f"{API_URL}/spc/{source}/{metric_name}", timeout=5)
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=30)
def get_metrics_history(source, metric_name, limit=200):
    try:
        r = requests.get(
            f"{API_URL}/metrics/history/{source}/{metric_name}",
            params={"limit": limit},
            timeout=5
        )
        return r.json()
    except Exception:
        return []