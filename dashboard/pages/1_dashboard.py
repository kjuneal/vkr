import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import get_all_states, metric_label, show_alerts


st.title("📊 Дашборд качества данных")
st.caption("Обновление каждые 30 секунд")

show_alerts() 

if st.button("🔄 Обновить"):
    st.cache_data.clear()

states = get_all_states()

if not states:
    st.error("Нет данных — убедитесь что сервер запущен и агенты отработали")
    st.stop()


sources = {}
for s in states:
    src = s["source"]
    if src not in sources:
        sources[src] = []
    sources[src].append(s)

STATUS_EMOJI  = {"critical": "🔴", "warning": "🟡", "normal": "🟢", "collecting": "⚪"}
STATUS_LABEL  = {"critical": "КРИТИЧНО", "warning": "ВНИМАНИЕ", "normal": "НОРМА", "collecting": "Сбор данных"}
STATUS_COLOR  = {"critical": "#ff4b4b", "warning": "#ffa500", "normal": "#21c354", "collecting": "#aaaaaa"}

priority = {"critical": 3, "warning": 2, "normal": 1, "collecting": 0}

cols = st.columns(len(sources))

for col, (source_name, metrics) in zip(cols, sorted(sources.items())):
    worst  = max(metrics, key=lambda x: priority.get(x["status"], 0))
    status = worst["status"]
    color  = STATUS_COLOR[status]

    with col:
        # Цветная рамка через markdown + HTML
        st.markdown(
            f"""
            <div style="
                border: 2px solid {color};
                border-radius: 12px;
                padding: 16px 20px 8px 20px;
                margin-bottom: 8px;
                background: {'#fff5f5' if status == 'critical' else '#fffbf0' if status == 'warning' else '#f0fff4' if status == 'normal' else '#fafafa'};
            ">
                <div style="font-size:18px; font-weight:700; color:#1a1a1a; margin-bottom:4px;">
                    {STATUS_EMOJI[status]} {source_name.upper()}
                </div>
                <div style="font-size:13px; font-weight:600; color:{color}; letter-spacing:1px; margin-bottom:12px;">
                    {STATUS_LABEL[status]}
                </div>
            """,
            unsafe_allow_html=True
        )

        for m in metrics:
            emoji = STATUS_EMOJI[m["status"]]
            val   = m.get("last_value") or m.get("ewma_z")

            if m["status"] == "collecting":
                delta_str = f"сбор: {m['n_baseline']}/5"
            elif m["mu_hat"] and m["sigma_hat"] and val and float(m["sigma_hat"]) != 0:
                delta = (float(val) - float(m["mu_hat"])) / float(m["sigma_hat"])
                delta_str = f"{delta:+.2f}σ"
            else:
                delta_str = "—"

            st.metric(
                label=f"{emoji} {metric_label(m['metric_name'])}",
                value=f"{float(val):.3f}" if val is not None else "—",
                delta=delta_str
            )

        st.markdown(
            f"<div style='font-size:11px; color:#999; margin-top:8px;'>обновлено: {worst['updated_at'][:19]}</div></div>",
            unsafe_allow_html=True
        )

st.divider()

st.subheader("🚨 Активные сигналы")
alerts = [s for s in states if s["status"] in ("critical", "warning")]

if not alerts:
    st.success("Сигналов нет — все источники в норме")
else:
    for a in sorted(alerts, key=lambda x: priority.get(x["status"], 0), reverse=True):
        methods = []
        if a["signal_shewhart"]: methods.append("Шухарт")
        if a["signal_cusum"]:    methods.append("CUSUM")
        if a["signal_ewma"]:     methods.append("EWMA")
        method_str = " + ".join(methods) if methods else "—"
        time_str   = a["last_signal_at"][:19] if a["last_signal_at"] else "—"

        if a["status"] == "critical":
            st.error(f"**{a['source']}** · {metric_label(a['metric_name'])} · {method_str} · {time_str}")
        else:
            st.warning(f"**{a['source']}** · {metric_label(a['metric_name'])} · {method_str} · {time_str}")