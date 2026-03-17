import streamlit as st

st.set_page_config(
    page_title="Data Quality Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

pages = {
    "Мониторинг": [
        st.Page("pages/4_experiment.py", title="Управление экспериментом", icon="🧪"),
        st.Page("pages/1_dashboard.py",  title="Дашборд",          icon="🟢"),
        st.Page("pages/2_analysis.py",   title="Детальный анализ",  icon="📈"),
        st.Page("pages/3_events.py",     title="Журнал событий",    icon="🔔"),
    ]
}

pg = st.navigation(pages)
pg.run()