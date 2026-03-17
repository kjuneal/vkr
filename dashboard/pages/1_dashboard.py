import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api import get_all_states, metric_label


st.title("📊 Дашборд качества данных")
st.caption("Обновление каждые 30 секунд")

if st.button("🔄 Обновить"):
    st.cache_data.clear()



states = get_all_states()

if not states:
    st.error("Нет данных — убедитесь что сервер запущен и агенты отработали")
    st.stop()

# Группируем по источнику
sources = {}
for s in states:
    src = s["source"]
    if src not in sources:
        sources[src] = []
    sources[src].append(s)

STATUS_EMOJI = {"critical": "🔴", "warning": "🟡", "normal": "🟢", "collecting": "⚪"}
STATUS_LABEL = {"critical": "КРИТИЧНО", "warning": "ВНИМАНИЕ", "normal": "НОРМА", "collecting": "Сбор данных"}

# Карточки источников
cols = st.columns(len(sources))

for col, (source_name, metrics) in zip(cols, sources.items()):
    with col:
        # Общий статус источника = наихудший из метрик
        priority = {"critical": 3, "warning": 2, "normal": 1, "collecting": 0}
        worst = max(metrics, key=lambda x: priority.get(x["status"], 0))
        status = worst["status"]

        st.markdown(f"### {STATUS_EMOJI[status]} {source_name.upper()}")
        st.markdown(f"**{STATUS_LABEL[status]}**")
        st.divider()

        for m in metrics:
            emoji = STATUS_EMOJI[m["status"]]
            
            # последнее значение метрики берём из истории через отдельный запрос
            # пока просто показываем статистику из spc_state
            val = m.get("last_value") or m.get("ewma_z")  # текущее EWMA как приближение последнего значения

            if m["status"] == "collecting":
                delta_str = f"сбор: {m['n_baseline']}/5"
            elif m["mu_hat"] and m["sigma_hat"] and val and m["sigma_hat"] != 0:
                delta = (float(val) - float(m["mu_hat"])) / float(m["sigma_hat"])
                delta_str = f"{delta:+.2f}σ"
            else:
                delta_str = "—"

            st.metric(
                label=f"{emoji} {metric_label(m['metric_name'])}",
                value=f"{float(val):.3f}" if val is not None else "—",
                delta=delta_str
            )

        st.caption(f"обновлено: {worst['updated_at'][:19]}")

st.divider()

# Активные сигналы
st.subheader("🚨 Активные сигналы")
alerts = [s for s in states if s["status"] in ("critical", "warning")]

if not alerts:
    st.success("Сигналов нет — все источники в норме")
else:
    for a in sorted(alerts, key=lambda x: x["status"] == "critical", reverse=True):
        methods = []
        if a["signal_shewhart"]: methods.append("Шухарт")
        if a["signal_cusum"]:    methods.append("CUSUM")
        if a["signal_ewma"]:     methods.append("EWMA")
        method_str = " + ".join(methods)

        if a["status"] == "critical":
            st.error(f"**{a['source']}** · {a['metric_name']} · {method_str} · {a['last_signal_at'][:19] if a['last_signal_at'] else '—'}")
        else:
            st.warning(f"**{a['source']}** · {a['metric_name']} · {method_str} · {a['last_signal_at'][:19] if a['last_signal_at'] else '—'}")