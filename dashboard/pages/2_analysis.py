import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import get_all_states, get_state, get_metrics_history, metric_label, show_alerts, get_experiment_config

st.title("📈 Детальный анализ")

show_alerts() 


states = get_all_states()
if not states:
    st.error("Нет данных")
    st.stop()

sources = sorted(set(s["source"] for s in states))
col1, col2 = st.columns(2)
with col1:
    source = st.selectbox("Источник", sources)
with col2:
    metrics_for_source = [s["metric_name"] for s in states if s["source"] == source]
    metric = st.selectbox("Метрика", options=metrics_for_source, format_func=metric_label)

if st.button("🔄 Обновить"):
    st.cache_data.clear()

state   = get_state(source, metric)
history = get_metrics_history(source, metric)

if not state or state.get("error"):
    st.warning("Нет данных для этой метрики")
    st.stop()

STATUS_EMOJI = {"critical": "🔴", "warning": "🟡", "normal": "🟢", "collecting": "⚪"}
STATUS_LABEL_RU = {"critical": "КРИТИЧНО", "warning": "ВНИМАНИЕ", "normal": "НОРМА", "collecting": "Сбор данных"}
STATUS_COLOR = {"critical": "#ff4b4b", "warning": "#ffa500", "normal": "#21c354", "collecting": "#aaaaaa"}

status_key = state["status"]
color = STATUS_COLOR[status_key]

# --- Блок статистик ---
mu_str    = f"{float(state['mu_hat']):.3f}"    if state['mu_hat']    else "сбор..."
sigma_str = f"{float(state['sigma_hat']):.3f}" if state['sigma_hat'] else "сбор..."

m1, m2, m3, m4 = st.columns(4)

m1.markdown(f"""
<div style="background:#f8f9fa; border-radius:10px; padding:14px 18px; border-left: 4px solid {color};">
    <div style="font-size:13px; color:#666; margin-bottom:6px; font-weight:500;">Статус</div>
    <div style="font-size:20px; font-weight:700; color:{color};">
        {STATUS_EMOJI[status_key]} {STATUS_LABEL_RU[status_key]}
    </div>
</div>
""", unsafe_allow_html=True)

m2.markdown(f"""
<div style="background:#f8f9fa; border-radius:10px; padding:14px 18px;">
    <div style="font-size:13px; color:#666; margin-bottom:6px; font-weight:500;">μ̂ (среднее)</div>
    <div style="font-size:20px; font-weight:600; color:#1a1a1a;">{mu_str}</div>
</div>
""", unsafe_allow_html=True)

m3.markdown(f"""
<div style="background:#f8f9fa; border-radius:10px; padding:14px 18px;">
    <div style="font-size:13px; color:#666; margin-bottom:6px; font-weight:500;">σ̂ (стд. откл.)</div>
    <div style="font-size:20px; font-weight:600; color:#1a1a1a;">{sigma_str}</div>
</div>
""", unsafe_allow_html=True)

m4.markdown(f"""
<div style="background:#f8f9fa; border-radius:10px; padding:14px 18px;">
    <div style="font-size:13px; color:#666; margin-bottom:6px; font-weight:500;">Наблюдений</div>
    <div style="font-size:20px; font-weight:600; color:#1a1a1a;">{state['n_baseline']}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

# --- Информация об эксперименте ---
exp_config = get_experiment_config()
if exp_config and "sources" in exp_config and source in exp_config["sources"]:
    src_cfg = exp_config["sources"][source]
    deg_label = src_cfg.get("label", "—")
    deg_start = src_cfg.get("deg_start", "—")
    deg_value = src_cfg.get("deg_value", "—")
    n_total   = src_cfg.get("n", "—")
    mu_exp    = exp_config.get("mu", "—")
    sigma_exp = exp_config.get("sigma", "—")

    st.markdown(f"""
    <div style="background:#f0f4ff; border-radius:10px; padding:16px 20px;
                border-left: 4px solid #4a90d9; margin-bottom:16px;">
        <div style="font-size:15px; color:#4a6fa5; font-weight:600; margin-bottom:12px;">
            🧪 Параметры эксперимента · {source}
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:24px 40px; align-items:flex-start;">
            <div>
                <div style="color:#888; font-size:12px; margin-bottom:4px;">Записей</div>
                <div style="font-weight:600; color:#1a1a1a; font-size:15px;">{n_total}</div>
            </div>
            <div>
                <div style="color:#888; font-size:12px; margin-bottom:4px;">μ (среднее)</div>
                <div style="font-weight:600; color:#1a1a1a; font-size:15px;">{mu_exp}</div>
            </div>
            <div>
                <div style="color:#888; font-size:12px; margin-bottom:4px;">σ (стд. откл.)</div>
                <div style="font-weight:600; color:#1a1a1a; font-size:15px;">{sigma_exp}</div>
            </div>
            <div>
                <div style="color:#888; font-size:12px; margin-bottom:4px;">Аномалия</div>
                <div style="font-weight:600; color:#1a1a1a; font-size:15px;">{deg_label}</div>
            </div>
            <div>
                <div style="color:#888; font-size:12px; margin-bottom:4px;">Начало деградации</div>
                <div style="font-weight:600; color:#1a1a1a; font-size:15px;">запись №{deg_start}</div>
            </div>
            <div>
                <div style="color:#888; font-size:12px; margin-bottom:4px;">Параметр деградации</div>
                <div style="font-weight:600; color:#1a1a1a; font-size:15px;">{deg_value}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


if state["status"] == "collecting":
    st.info(f"Идёт сбор baseline: {state['n_baseline']} наблюдений.")
    st.stop()

if not history:
    st.warning("История метрик пуста")
    st.stop()

timestamps = [h["timestamp"] for h in history]
values     = [h["value"]     for h in history]
mu         = float(state["mu_hat"])
sigma      = float(state["sigma_hat"]) if state["sigma_hat"] else 1e-9
ucl        = float(state["ucl"])
lcl        = float(state["lcl"])

# EWMA
lam  = 0.2
ewma = [mu]
for v in values[1:]:
    ewma.append(lam * v + (1 - lam) * ewma[-1])
ewma_sigma = sigma * np.sqrt(lam / (2 - lam))
ewma_ucl   = mu + 3 * ewma_sigma
ewma_lcl   = mu - 3 * ewma_sigma

# CUSUM
k, h_val = 0.5 * sigma, 5.0 * sigma
cp, cn   = 0.0, 0.0
cusum_pos, cusum_neg = [], []
for v in values:
    cp = max(0, cp + (v - mu) - k)
    cn = max(0, cn - (v - mu) - k)
    cusum_pos.append(cp)
    cusum_neg.append(cn)

# ── График 1: Шухарт + EWMA ───────────────────────────────────────────────
st.markdown("---")
st.markdown(f"### 📉 Контрольная карта Шухарта + EWMA — {metric_label(metric)} · {source}")
#st.caption("Синие точки — наблюдения · Оранжевая линия — EWMA (сглаженный тренд) · Красные пунктиры — границы Шухарта ±3σ · Оранжевые пунктиры — границы EWMA")
st.markdown("""
<div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:8px; font-size:12px; color:#555;">
    <span>🔵 Наблюдения</span>
    <span>🟠 EWMA — сглаженный тренд</span>
    <span><span style="color:#e74c3c;">- -</span> UCL/LCL Шухарта ±3σ</span>
    <span><span style="color:#f39c12;">- -</span> UCL/LCL EWMA</span>
    <span>✖ Сигнал Шухарта</span>
</div>
""", unsafe_allow_html=True)

fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=timestamps, y=values,
    mode="markers", name="Наблюдения",
    marker=dict(color="#1a73e8", size=7, opacity=0.8)
))
fig1.add_trace(go.Scatter(
    x=timestamps, y=ewma,
    mode="lines", name="EWMA (тренд)",
    line=dict(color="#f39c12", width=2.5)
))

# Границы
for y_val, name, color, dash in [
    (ucl,      "UCL (Шухарт)",  "#e74c3c", "dash"),
    (lcl,      "LCL (Шухарт)",  "#e74c3c", "dash"),
    (mu,       "μ̂ (среднее)",   "#2ecc71", "dot"),
    (ewma_ucl, "UCL (EWMA)",    "#f39c12", "dashdot"),
    (ewma_lcl, "LCL (EWMA)",    "#f39c12", "dashdot"),
]:
    fig1.add_hline(
        y=y_val, line_dash=dash, line_color=color, line_width=1.5,
        annotation_text=name, annotation_position="right",
        annotation_font_size=11
    )

# Сигналы Шухарта
sx = [t for t, v in zip(timestamps, values) if v > ucl or v < lcl]
sy = [v for v in values if v > ucl or v < lcl]
if sx:
    fig1.add_trace(go.Scatter(
        x=sx, y=sy, mode="markers", name="⚠ Сигнал Шухарта",
        marker=dict(color="#e74c3c", size=12, symbol="x-thin", line_width=2)
    ))

fig1.update_layout(
    height=380,
    margin=dict(r=120, t=20, b=40),
    showlegend=False,
    xaxis_title="Время",
    yaxis_title=metric_label(metric),
    hovermode="x unified",
    plot_bgcolor="#fafafa",
    paper_bgcolor="white",
)
st.plotly_chart(fig1, use_container_width=True)

# ── График 2: CUSUM ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"### 📊 CUSUM — {metric_label(metric)} · {source}")
#st.caption(f"Зелёная линия C⁺ — накопленные положительные отклонения · Фиолетовая C⁻ — отрицательные · Красный пунктир — порог h = {h_val:.2f}")

st.markdown(f"""
<div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:8px; font-size:12px; color:#555;">
    <span style="color:#2ecc71;">── C⁺ накопленные отклонения вверх</span>
    <span style="color:#9b59b6;">── C⁻ накопленные отклонения вниз</span>
    <span><span style="color:#e74c3c;">- -</span> Порог h = {h_val:.2f}</span>
    <span>✖ Сигнал CUSUM</span>
</div>
""", unsafe_allow_html=True)

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=timestamps, y=cusum_pos,
    mode="lines", name="C⁺ (сдвиг вверх)",
    line=dict(color="#2ecc71", width=2.5)
))
fig2.add_trace(go.Scatter(
    x=timestamps, y=cusum_neg,
    mode="lines", name="C⁻ (сдвиг вниз)",
    line=dict(color="#9b59b6", width=2.5)
))
fig2.add_hline(
    y=h_val, line_dash="dash", line_color="#e74c3c", line_width=1.5,
    annotation_text=f"Порог h = {h_val:.2f}",
    annotation_position="right", annotation_font_size=11
)

# Точки сигналов CUSUM
cx = [t for t, c in zip(timestamps, cusum_pos) if c > h_val]
cy = [c for c in cusum_pos if c > h_val]
if cx:
    fig2.add_trace(go.Scatter(
        x=cx, y=cy, mode="markers", name="⚠ Сигнал CUSUM",
        marker=dict(color="#e74c3c", size=10, symbol="x-thin", line_width=2)
    ))

fig2.update_layout(
    height=280,
    margin=dict(r=120, t=20, b=40),
    showlegend=False,
    xaxis_title="Время",
    yaxis_title="Значение статистики",
    hovermode="x unified",
    plot_bgcolor="#fafafa",
    paper_bgcolor="white",
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("Текущие значения статистик SPC")
c1, c2, c3 = st.columns(3)
c1.metric("C⁺ (CUSUM)", f"{float(state['cusum_pos']):.3f}", delta=f"порог {h_val:.2f}")
c2.metric("C⁻ (CUSUM)", f"{float(state['cusum_neg']):.3f}", delta=f"порог {h_val:.2f}")
c3.metric("Z (EWMA)",   f"{float(state['ewma_z']):.3f}" if state["ewma_z"] else "—")

st.markdown("---")
st.markdown("### Состояние методов контроля")

cols = st.columns(3)

def method_status_box(col, name, signal, is_warning=False):
    if signal:
        color  = "#ffa500" if is_warning else "#ff4b4b"
        label  = "ВНИМАНИЕ" if is_warning else "КРИТИЧНО"
        bg     = "#fffbf0" if is_warning else "#fff5f5"
    else:
        color, label, bg = "#21c354", "НОРМА", "#f0fff4"

    col.markdown(f"""
    <div style="background:{bg}; border-radius:10px; padding:16px;
                border-left: 4px solid {color}; text-align:center;">
        <div style="font-size:14px; color:#444; font-weight:600;
                    margin-bottom:8px; letter-spacing:0.5px;">{name}</div>
        <div style="font-size:17px; font-weight:700; color:{color};">{label}</div>
    </div>
    """, unsafe_allow_html=True)

method_status_box(cols[0], "Шухарт", state["signal_shewhart"])
method_status_box(cols[1], "CUSUM",  state["signal_cusum"])
method_status_box(cols[2], "EWMA",   state["signal_ewma"], is_warning=True)