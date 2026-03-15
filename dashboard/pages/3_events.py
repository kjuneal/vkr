import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api import get_all_states, metric_label

st.title("🔔 Журнал событий")

if st.button("🔄 Обновить"):
    st.cache_data.clear()

states = get_all_states()
alerts = [s for s in states if s["last_signal_at"] is not None]

if not alerts:
    st.info("Сигналов пока не было")
    st.stop()

# Собираем таблицу
rows = []
for a in alerts:
    methods = []
    if a["signal_shewhart"]: methods.append("Шухарт")
    if a["signal_cusum"]:    methods.append("CUSUM")
    if a["signal_ewma"]:     methods.append("EWMA")

    rows.append({
        "Время":    a["last_signal_at"][:19] if a["last_signal_at"] else "—",
        "Источник": a["source"],
        "Метрика": metric_label(a["metric_name"]),
        "Методы":   " + ".join(methods) if methods else "—",
        "Статус":   a["status"].upper(),
        "UCL":      f"{a['ucl']:.3f}" if a["ucl"] else "—",
        "LCL":      f"{a['lcl']:.3f}" if a["lcl"] else "—",
        "C⁺":       f"{a['cusum_pos']:.3f}",
        "C⁻":       f"{a['cusum_neg']:.3f}",
        "EWMA Z":   f"{a['ewma_z']:.3f}" if a["ewma_z"] else "—",
    })

df = pd.DataFrame(rows)

# Фильтры
col1, col2 = st.columns(2)
with col1:
    filter_source = st.multiselect("Источник", options=df["Источник"].unique(), default=list(df["Источник"].unique()))
with col2:
    filter_status = st.multiselect("Статус", options=df["Статус"].unique(), default=list(df["Статус"].unique()))

df_filtered = df[df["Источник"].isin(filter_source) & df["Статус"].isin(filter_status)]

st.caption(f"Показано {len(df_filtered)} событий")

# Подсветка строк
def highlight_status(row):
    if row["Статус"] == "CRITICAL":
        return ["background-color: #ffcccc; color: #8b0000"] * len(row)
    elif row["Статус"] == "WARNING":
        return ["background-color: #fff3cd; color: #856404"] * len(row)
    return [""] * len(row)

st.dataframe(
    df_filtered.style.apply(highlight_status, axis=1),
    use_container_width=True,
    hide_index=True,
    height=400
)