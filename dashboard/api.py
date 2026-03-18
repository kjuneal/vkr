import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"

METRIC_LABELS = {
    "mean":         "Среднее",
    "std":          "Стд. отклонение",
    "completeness": "Полнота",
    "median":       "Медиана",
    "iqr":          "МКР (IQR)",
    "count":        "Количество",
    "missing_count":"Пропуски",
}

def reset_experiment():
    try:
        r = requests.delete(f"{API_URL}/reset/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

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
    
def save_experiment_config(config: dict):
    try:
        r = requests.post(f"{API_URL}/experiment/config/", json=config, timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=60)
def get_experiment_config():
    try:
        r = requests.get(f"{API_URL}/experiment/config/", timeout=5)
        return r.json()
    except Exception:
        return {}
    
def show_alerts(states=None):
    """Показывает toast-уведомления о новых сигналах. Вызывать в начале каждой страницы."""
    if states is None:
        states = get_all_states()

    if "seen_signals" not in st.session_state:
        st.session_state.seen_signals = set()

    alerts = [s for s in states if s["status"] in ("critical", "warning")]

    for a in alerts:
        signal_key = f"{a['source']}_{a['metric_name']}_{a['last_signal_at']}"

        if signal_key not in st.session_state.seen_signals:
            st.session_state.seen_signals.add(signal_key)

            if a["status"] == "critical":
                st.toast(
                    f"🔴 {a['source']} · {metric_label(a['metric_name'])} · КРИТИЧНО",
                    icon="🚨"
                )
            else:
                st.toast(
                    f"🟡 {a['source']} · {metric_label(a['metric_name'])} · ВНИМАНИЕ",
                    icon="⚠️"
                )