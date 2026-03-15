import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api import get_all_states, get_state, get_metrics_history, metric_label

st.title("📈 Детальный анализ")

states = get_all_states()
if not states:
    st.error("Нет данных")
    st.stop()

# Селекторы
sources   = sorted(set(s["source"] for s in states))
col1, col2 = st.columns(2)

with col1:
    source = st.selectbox("Источник", sources)
with col2:
    metrics_for_source = [s["metric_name"] for s in states if s["source"] == source]
    metric = st.selectbox(
    "Метрика",
    options=metrics_for_source,
    format_func=metric_label  # ← показывает русское название, но значение остаётся английским
)

if st.button("🔄 Обновить"):
    st.cache_data.clear()

state   = get_state(source, metric)
history = get_metrics_history(source, metric)

if not state or state.get("error"):
    st.warning("Нет данных для этой метрики")
    st.stop()

# Метрики статуса
STATUS_EMOJI = {"critical": "🔴", "warning": "🟡", "normal": "🟢", "collecting": "⚪"}
m1, m2, m3, m4 = st.columns(4)
m1.metric("Статус",   f"{STATUS_EMOJI[state['status']]} {state['status'].upper()}")
m2.metric("μ̂ (среднее)", f"{state['mu_hat']:.3f}"   if state['mu_hat']    else "сбор...")
m3.metric("σ̂ (стд)", f"{state['sigma_hat']:.3f}"    if state['sigma_hat'] else "сбор...")
m4.metric("Наблюдений", f"{state['n_baseline']}")

if state["status"] == "collecting":
    st.info(f"Идёт сбор baseline: {state['n_baseline']} наблюдений. Анализ начнётся после накопления достаточного количества данных.")
    st.stop()

if not history:
    st.warning("История метрик пуста")
    st.stop()

# Данные для графиков
timestamps = [h["timestamp"] for h in history]
values     = [h["value"]     for h in history]

ucl = state["ucl"]
lcl = state["lcl"]
mu  = state["mu_hat"]
sigma = state["sigma_hat"]

# EWMA
lam = 0.2
ewma = [mu]
for v in values[1:]:
    ewma.append(lam * v + (1 - lam) * ewma[-1])

import numpy as np
ewma_sigma = sigma * np.sqrt(lam / (2 - lam))
ewma_ucl = mu + 3 * ewma_sigma
ewma_lcl = mu - 3 * ewma_sigma

# ── График 1: Шухарт + EWMA ──
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    subplot_titles=("Контрольная карта Шухарта + EWMA", "CUSUM"),
    row_heights=[0.65, 0.35],
    vertical_spacing=0.1
)

# Наблюдения
fig.add_trace(go.Scatter(
    x=timestamps, y=values,
    mode="markers", name="Наблюдения",
    marker=dict(color="#1a73e8", size=6, opacity=0.8)
), row=1, col=1)

# EWMA
fig.add_trace(go.Scatter(
    x=timestamps, y=ewma,
    mode="lines", name="EWMA",
    line=dict(color="#f39c12", width=2)
), row=1, col=1)

# UCL / LCL / CL
for y, name, color, dash in [
    (ucl, "UCL", "#e74c3c", "dash"),
    (lcl, "LCL", "#e74c3c", "dash"),
    (mu,  "μ̂",  "#2ecc71", "dot"),
    (ewma_ucl, "UCL EWMA", "#f39c12", "dashdot"),
    (ewma_lcl, "LCL EWMA", "#f39c12", "dashdot"),
]:
    fig.add_hline(y=y, line_dash=dash, line_color=color,
                  line_width=1, annotation_text=name,
                  annotation_position="right", row=1, col=1)

# Точки-сигналы Шухарта
signal_x = [t for t, v in zip(timestamps, values) if v > ucl or v < lcl]
signal_y = [v for v in values if v > ucl or v < lcl]
if signal_x:
    fig.add_trace(go.Scatter(
        x=signal_x, y=signal_y,
        mode="markers", name="Сигнал Шухарта",
        marker=dict(color="#e74c3c", size=10, symbol="x")
    ), row=1, col=1)

# ── CUSUM ──
k = 0.5 * sigma
h = 5.0 * sigma
cp, cn = 0.0, 0.0
cusum_pos, cusum_neg = [], []
for v in values:
    cp = max(0, cp + (v - mu) - k)
    cn = max(0, cn - (v - mu) - k)
    cusum_pos.append(cp)
    cusum_neg.append(cn)

fig.add_trace(go.Scatter(
    x=timestamps, y=cusum_pos,
    mode="lines", name="C⁺",
    line=dict(color="#2ecc71", width=2)
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=timestamps, y=cusum_neg,
    mode="lines", name="C⁻",
    line=dict(color="#9b59b6", width=2)
), row=2, col=1)

fig.add_hline(y=h, line_dash="dash", line_color="#e74c3c",
              line_width=1, annotation_text=f"h={h:.2f}",
              annotation_position="right", row=2, col=1)

fig.update_layout(
    height=600,
    template="plotly_dark",
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(r=80)
)

st.plotly_chart(fig, use_container_width=True)

# Детали сигналов
st.subheader("Статистики SPC")
c1, c2, c3 = st.columns(3)
c1.metric("C⁺ (CUSUM)", f"{state['cusum_pos']:.3f}", delta=f"порог {h:.2f}")
c2.metric("C⁻ (CUSUM)", f"{state['cusum_neg']:.3f}", delta=f"порог {h:.2f}")
c3.metric("Z (EWMA)",   f"{state['ewma_z']:.3f}")

cols = st.columns(3)
cols[0].metric("Шухарт", "🔴 СИГНАЛ" if state["signal_shewhart"] else "🟢 норма")
cols[1].metric("CUSUM",  "🔴 СИГНАЛ" if state["signal_cusum"]    else "🟢 норма")
cols[2].metric("EWMA",   "🟡 СИГНАЛ" if state["signal_ewma"]     else "🟢 норма")