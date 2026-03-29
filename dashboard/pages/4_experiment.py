import streamlit as st
import threading
import time
import sqlite3
import sys, os

# Корень проекта в путь до всех локальных импортов
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from data_generate import generate_data

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import reset_experiment, show_alerts, save_experiment_config
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, text

# Словарь пресетов 
PRESETS = {
    "1а — Сдвиг среднего (Δ=20)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "mean_shift", "deg_start_a": 200, "deg_val_a": 20.0,
        "n_b": 800, "deg_type_b": "mean_shift", "deg_start_b": 200, "deg_val_b": 20.0,
        "n_c": 800, "deg_type_c": "mean_shift", "deg_start_c": 200, "deg_val_c": 20.0,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "1б — Рост дисперсии (Δσ=10)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "variance", "deg_start_a": 200, "deg_val_a": 10.0,
        "n_b": 800, "deg_type_b": "variance", "deg_start_b": 200, "deg_val_b": 10.0,
        "n_c": 800, "deg_type_c": "variance", "deg_start_c": 200, "deg_val_c": 10.0,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "1в — Постепенный дрейф (δ=0.3)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "gradual_drift", "deg_start_a": 200, "deg_val_a": 0.3,
        "n_b": 800, "deg_type_b": "gradual_drift", "deg_start_b": 200, "deg_val_b": 0.3,
        "n_c": 800, "deg_type_c": "gradual_drift", "deg_start_c": 200, "deg_val_c": 0.3,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "1г — Пропуски (30%)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "missing", "deg_start_a": 200, "deg_val_a": 0.3,
        "n_b": 800, "deg_type_b": "missing", "deg_start_b": 200, "deg_val_b": 0.3,
        "n_c": 800, "deg_type_c": "missing", "deg_start_c": 200, "deg_val_c": 0.3,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "1д — Случайные выбросы (15%)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "spikes", "deg_start_a": 200, "deg_val_a": 0.15,
        "n_b": 800, "deg_type_b": "spikes", "deg_start_b": 200, "deg_val_b": 0.15,
        "n_c": 800, "deg_type_c": "spikes", "deg_start_c": 200, "deg_val_c": 0.15,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "2а — Сдвиг 1σ (Δ=5)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "mean_shift", "deg_start_a": 200, "deg_val_a": 5.0,
        "n_b": 800, "deg_type_b": "mean_shift", "deg_start_b": 200, "deg_val_b": 5.0,
        "n_c": 800, "deg_type_c": "mean_shift", "deg_start_c": 200, "deg_val_c": 5.0,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "2б — Сдвиг 2σ (Δ=10)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "mean_shift", "deg_start_a": 200, "deg_val_a": 10.0,
        "n_b": 800, "deg_type_b": "mean_shift", "deg_start_b": 200, "deg_val_b": 10.0,
        "n_c": 800, "deg_type_c": "mean_shift", "deg_start_c": 200, "deg_val_c": 10.0,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "2в — Сдвиг 3σ (Δ=15)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "mean_shift", "deg_start_a": 200, "deg_val_a": 15.0,
        "n_b": 800, "deg_type_b": "mean_shift", "deg_start_b": 200, "deg_val_b": 15.0,
        "n_c": 800, "deg_type_c": "mean_shift", "deg_start_c": 200, "deg_val_c": 15.0,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "2г — Сдвиг 5σ (Δ=25)": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "mean_shift", "deg_start_a": 200, "deg_val_a": 25.0,
        "n_b": 800, "deg_type_b": "mean_shift", "deg_start_b": 200, "deg_val_b": 25.0,
        "n_c": 800, "deg_type_c": "mean_shift", "deg_start_c": 200, "deg_val_c": 25.0,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "3а — Выбросы 10%": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "spikes", "deg_start_a": 200, "deg_val_a": 0.1,
        "n_b": 800, "deg_type_b": "spikes", "deg_start_b": 200, "deg_val_b": 0.1,
        "n_c": 800, "deg_type_c": "spikes", "deg_start_c": 200, "deg_val_c": 0.1,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
    "3б — Выбросы 25%": {
        "mu": 100.0, "sigma": 5.0, "window_size": 20, "delay": 0,
        "n_a": 800, "deg_type_a": "spikes", "deg_start_a": 200, "deg_val_a": 0.25,
        "n_b": 800, "deg_type_b": "spikes", "deg_start_b": 200, "deg_val_b": 0.25,
        "n_c": 800, "deg_type_c": "spikes", "deg_start_c": 200, "deg_val_c": 0.25,
        "sel_a": ["mean","median","std","completeness","iqr"],
        "sel_b": ["mean","median","std","completeness","iqr"],
        "sel_c": ["mean","median","std","completeness","iqr"],
    },
}

# ── Константы ─────────────────────────────────────────────────────────────

SERVER_URL  = "http://127.0.0.1:8000"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH    = os.path.join(ROOT, "data", "source_c.csv")
SQLITE_PATH = os.path.join(ROOT, "source_b.db")
PG_DB_NAME  = "source_a.db" 

# ── Генераторы данных ──────────────────────────────────────────────────────

def load_to_postgres(df, db_name):
    url = URL.create(
        drivername="postgresql+psycopg2",
        username="postgres",
        password="12345",
        host="localhost",
        port=5432,
        database=db_name,
    )
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS data"))
    df.to_sql("data", engine, index=False, if_exists="replace")


def load_to_sqlite(df, path):
    conn = sqlite3.connect(path)
    df.to_sql("data", conn, index=False, if_exists="replace")
    conn.close()


def load_to_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


# ── Запуск агентов ─────────────────────────────────────────────────────────

def run_agent_a(window_size, delay, selected, status_dict):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ["PGCLIENTENCODING"] = "UTF8"
    from agents.agent_a import AgentA
    try:
        agent = AgentA(PG_DB_NAME, SERVER_URL, window_size, delay, selected)
        agent.run()
        status_dict["a"] = "✅ завершён"
    except Exception as e:
        status_dict["a"] = f"❌ ошибка: {e}"


def run_agent_b(window_size, delay, selected, status_dict):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from agents.agent_b import AgentB
    try:
        agent = AgentB(SQLITE_PATH, SERVER_URL, window_size, delay, selected)
        agent.run()
        status_dict["b"] = "✅ завершён"
    except Exception as e:
        status_dict["b"] = f"❌ ошибка: {e}"


def run_agent_c(window_size, delay, selected, status_dict):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from agents.agent_c import AgentC
    try:
        agent = AgentC(CSV_PATH, SERVER_URL, window_size, delay, selected)
        agent.run()
        status_dict["c"] = "✅ завершён"
    except Exception as e:
        status_dict["c"] = f"❌ ошибка: {e}"

# ── Интерфейс ──────────────────────────────────────────────────────────────

st.title("🧪 Управление экспериментом")

show_alerts()

st.caption("Настройте параметры, нажмите «Начать» — система сгенерирует данные и запустит агентов")

st.divider()

st.subheader("⚡ Быстрый запуск по пресету")
col_p1, col_p2 = st.columns([3, 1])
with col_p1:
    preset_name = st.selectbox(
        "Выбери пресет эксперимента",
        options=["— выбрать —"] + list(PRESETS.keys()),
        label_visibility="collapsed"
    )
with col_p2:
    load_preset = st.button("Загрузить", type="secondary", use_container_width=True)

if load_preset and preset_name != "— выбрать —":
    pr = PRESETS[preset_name]
    st.session_state.update({
        "mu": pr["mu"], "sigma": pr["sigma"],
        "window_size": pr["window_size"], "delay": pr["delay"],
        "n_a": pr["n_a"], "deg_type_a": pr["deg_type_a"],
        "deg_start_a": pr["deg_start_a"], "deg_val_a": pr["deg_val_a"],
        "n_b": pr["n_b"], "deg_type_b": pr["deg_type_b"],
        "deg_start_b": pr["deg_start_b"], "deg_val_b": pr["deg_val_b"],
        "n_c": pr["n_c"], "deg_type_c": pr["deg_type_c"],
        "deg_start_c": pr["deg_start_c"], "deg_val_c": pr["deg_val_c"],
        "sel_a": pr["sel_a"], "sel_b": pr["sel_b"], "sel_c": pr["sel_c"],
    })
    st.success(f"Загружен пресет: {preset_name}")
    st.rerun()

st.divider()

# Общие параметры
st.subheader("⚙️ Общие параметры")
col1, col2, col3 = st.columns(3)
with col1:
    mu = st.number_input(
        "Базовое среднее (μ)", 
        step=1.0,
        #value=st.session_state.get("mu", 100.0),  
        key="mu", 
        help="Ожидаемое среднее значение данных в нормальном режиме. "
             "Например, 100 означает что данные будут генерироваться около этого значения."
    )
with col2:
    sigma = st.number_input(
        "Базовое стд. откл. (σ)",
        step=0.5, min_value=0.1,
        value=st.session_state.get("sigma", 5.0),
        key="sigma",
        help="Разброс данных в нормальном режиме. Чем больше σ, тем шире разброс. "
             "Рекомендуется: 3–10 для наглядного эксперимента."
    )
with col3:
    window_size = st.number_input(
        "Размер окна агента", step=5, min_value=5,
        value=st.session_state.get("window_size", 20),
        key="window_size",
        help="Сколько записей обрабатывает агент за один цикл. "
             "По этому окну вычисляются метрики (среднее, стд. откл., полнота). "
             "Меньше окно — больше точек на графике, но больше шума."
    )

col4, _ = st.columns(2)
with col4:
    delay = st.number_input(
        "Задержка между окнами (сек)", step=1, min_value=0,
        value=st.session_state.get("delay", 0),
        key="delay",
        help="Пауза между отправками метрик агентом. "
             "0 — максимальная скорость, 2–3 — удобно наблюдать в реальном времени."
    )
st.divider()

ALL_METRICS = {
    "mean":         "Среднее",
    "std":          "Стд. отклонение",
    "completeness": "Полнота",
    "median":       "Медиана",
    "iqr":          "МКР (IQR)",
}
DEGRADATION_OPTIONS = {
    "none":          "Без деградации",
    "mean_shift":    "Сдвиг среднего",
    "variance":      "Рост дисперсии",
    "missing":       "Пропуски",
    "gradual_drift": "Постепенный дрейф",
    "spikes":        "Случайные выбросы",
}

# Подсказки по параметру деградации
DEG_PARAM_HELP = {
    "none":          ("—", "Параметр не используется", 0.0),
    "mean_shift":    ("Величина сдвига (Δ)", "На сколько единиц сдвинется среднее. Рекомендуется: 1σ–3σ", 20.0),
    "variance":      ("Доп. σ", "Насколько вырастет стандартное отклонение. Рекомендуется: 0.5σ–2σ", 10.0),
    "missing":       ("Доля пропусков", "Доля записей с NaN (0.0–0.5). 0.2 = 20% пропусков", 0.2),
    "gradual_drift": ("Дрейф за шаг", "Смещение среднего на каждую запись. Рекомендуется: 0.2–1.0", 0.5),
    "spikes":        ("Вероятность выброса", "Доля записей с резким отклонением (0.0–0.3). 0.1 = 10%", 0.1),
}

# Параметры источников
st.subheader("📦 Источник A — PostgreSQL")
col1, col2 = st.columns(2)
with col1:
    n_a = st.number_input(
        "Записей в источнике A", step=50, min_value=50,
        value=st.session_state.get("n_a", 500),
        key="n_a",
        help="Общее количество строк в таблице. "
             "Рекомендуется минимум 100 для корректной фазы I SPC + записи с деградацией."
    )
with col2:
    deg_type_a = st.selectbox(
        "Вид деградации",
        options=list(DEGRADATION_OPTIONS.keys()),
        format_func=lambda x: DEGRADATION_OPTIONS[x],
        index=list(DEGRADATION_OPTIONS.keys()).index(
            st.session_state.get("deg_type_a", "none")
        ),
        key="deg_type_a"
    )

col3, col4 = st.columns(2)
with col3:
    deg_start_a = st.number_input(
        "Начало деградации (запись №)", step=10,
        min_value=0, max_value=n_a - 1, key="deg_start_a",
        value=st.session_state.get("deg_start_a", 200),
        help="С какой записи начинается рост дисперсии. "
             "Записи до этого момента используются системой для обучения (фаза I). "
             "Рекомендуется: не менее 5 × размер окна.", disabled=(deg_type_a == "none")
    )
with col4:
    param_label, param_help, param_default = DEG_PARAM_HELP[deg_type_a]
    if deg_type_a == "none":
        deg_val_a = 0.0
        st.number_input(param_label if deg_type_a != "none" else "Параметр", value=0.0, disabled=True)
    else:
        deg_val_a = st.number_input(param_label, value=param_default, step=0.1, help=param_help, key="deg_val_a")

    # deg_val_a = st.number_input(
    #     "Доп. σ при росте дисперсии", value=10.0, step=1.0, min_value=0.0,
    #     help="Насколько увеличится разброс данных после начала деградации. "
    #          "Например, 10 означает что стандартное отклонение вырастет с базового σ до σ+10. "
    #          "Рекомендуется: 0.5σ–2σ для постепенного роста, >2σ для резкого."
    # )

selected_a = st.multiselect(
    "Метрики источника A",
    options=list(ALL_METRICS.keys()),
    default=st.session_state.get("sel_a", ["mean", "std"]), #default=["mean", "std"],
    format_func=lambda x: ALL_METRICS[x],
    key="sel_a",
    help="Какие метрики вычисляет агент A."
)
st.divider()

st.subheader("📦 Источник B — SQLite")
col1, col2 = st.columns(2)
with col1:
    n_b = st.number_input(
        "Записей в источнике B", step=50, min_value=50,
        value=st.session_state.get("n_b", 500),
        key="n_b",
        help="Общее количество строк. Аналогично источнику A."
    )
with col2:
    deg_type_b = st.selectbox(
        "Вид деградации",
        options=list(DEGRADATION_OPTIONS.keys()),
        format_func=lambda x: DEGRADATION_OPTIONS[x],
        index=list(DEGRADATION_OPTIONS.keys()).index(
            st.session_state.get("deg_type_b", "none")
        ),
        key="deg_type_b"
    )
col3, col4 = st.columns(2)
with col3:
    deg_start_b = st.number_input(
        "Начало деградации (запись №)", step=10,
        min_value=0, max_value=n_b - 1, key="deg_start_b",
        value=st.session_state.get("deg_start_b", 200),
        help="С какой записи начинают появляться пропущенные значения (NULL). "
             "До этой записи данные полные (полнота = 1.0).", disabled=(deg_type_b == "none")
    )
with col4:
    param_label, param_help, param_default = DEG_PARAM_HELP[deg_type_b]
    if deg_type_b == "none":
        deg_val_b = 0.0
        st.number_input("Параметр", value=0.0, disabled=True, key="val_b_dis")
    else:
        deg_val_b = st.number_input(param_label, value=param_default, step=0.1, help=param_help, key="deg_val_b")
        
    # deg_val_b = st.slider(
    #     "Доля пропусков", min_value=0.0, max_value=0.5, value=0.2, step=0.05,
    #     help="Какая доля записей будет содержать пропуски после начала деградации. "
    #          "0.05 = 5% пропусков (лёгкая деградация), "
    #          "0.20 = 20% (умеренная), "
    #          "0.50 = 50% (критическая)."
    # )
selected_b = st.multiselect(
    "Метрики источника B",
    options=list(ALL_METRICS.keys()),
    default=st.session_state.get("sel_b", ["completeness", "mean"]), #default=["completeness", "mean"],
    format_func=lambda x: ALL_METRICS[x],
    key="sel_b",
    help="Какие метрики вычисляет агент B."
)
st.divider()

st.subheader("📦 Источник C — CSV")
col1, col2 = st.columns(2)
with col1:
    n_c = st.number_input(
        "Записей в источнике C",
        step=50, min_value=50,
        value=st.session_state.get("n_c", 500),
        key="n_c",
        help="Общее количество строк. Аналогично источнику A."
    )
with col2:
    deg_type_c = st.selectbox(
        "Вид деградации",
        options=list(DEGRADATION_OPTIONS.keys()),
        format_func=lambda x: DEGRADATION_OPTIONS[x],
        index=list(DEGRADATION_OPTIONS.keys()).index(
            st.session_state.get("deg_type_c", "none")
        ),
        key="deg_type_c"
    )
col3, col4 = st.columns(2)   
with col3:
    deg_start_c = st.number_input(
        "Начало деградации (запись №)", step=10,
        min_value=0, max_value=n_c - 1, key="deg_start_c",
        value=st.session_state.get("deg_start_c", 200),
        help="С какой записи среднее значение начнёт смещаться. "
             "До этой записи данные генерируются с базовым μ.", disabled=(deg_type_c == "none")
    )
with col4:
    param_label, param_help, param_default = DEG_PARAM_HELP[deg_type_c]
    if deg_type_c == "none":
        deg_val_c = 0.0
        st.number_input("Параметр", value=0.0, disabled=True, key="val_c_dis")
    else:
        deg_val_c = st.number_input(param_label, value=param_default, step=0.1, help=param_help, key="deg_val_c")


    # deg_val_c = st.number_input(
    #     "Величина сдвига (Δ)", value=20.0, step=5.0,
    #     help="На сколько единиц сдвинется среднее после начала деградации. "
    #          "Например, при μ=100 и Δ=20 среднее станет ~120. "
    #          "Рекомендуется: 1σ–2σ для постепенного, >3σ для мгновенного обнаружения."
    # )

selected_c = st.multiselect(
    "Метрики источника C",
    options=list(ALL_METRICS.keys()),
    default=st.session_state.get("sel_c", ["mean", "std", "median"]), #default=["mean", "std", "median"],
    format_func=lambda x: ALL_METRICS[x],
    key="sel_c",
    help="Какие метрики вычисляет агент C."
)

# Кнопка запуска
if st.button("🚀 Начать эксперимент", type="primary", use_container_width=True):

    if not selected_a or not selected_b or not selected_c:
        st.error("Выберите хотя бы одну метрику для каждого источника!")
        st.stop()

    # 1. Очищаем старые данные
    with st.status("Подготовка...", expanded=True) as status:

        st.write("🗑️ Очистка старых данных в БД...")
        result = reset_experiment()
        if "error" in result:
            st.error(f"Ошибка очистки: {result['error']}")
            st.stop()
        
        st.write("💾 Сохранение параметров эксперимента...")
        config = {
            "mu": mu, "sigma": sigma,
            "sources": {
                "source_a": {
                    "n": n_a,
                    "degradation": deg_type_a,
                    "deg_start": deg_start_a,
                    "deg_value": deg_val_a,
                    "metrics": selected_a,
                    "label": DEGRADATION_OPTIONS[deg_type_a]
                },
                "source_b": {
                    "n": n_b,
                    "degradation": deg_type_b,
                    "deg_start": deg_start_b,
                    "deg_value": deg_val_b,
                    "metrics": selected_b,
                    "label": DEGRADATION_OPTIONS[deg_type_b]
                },
                "source_c": {
                    "n": n_c,
                    "degradation": deg_type_c,
                    "deg_start": deg_start_c,
                    "deg_value": deg_val_c,
                    "metrics": selected_c,
                    "label": DEGRADATION_OPTIONS[deg_type_c]
                },
            }
        }
        save_experiment_config(config)

        # 2. Генерация данных
        st.write("⚙️ Генерация данных для источника A...")
        df_a = generate_data(n_a, mu, sigma, deg_type_a, deg_start_a, deg_val_a)
        load_to_postgres(df_a, PG_DB_NAME)

        st.write("⚙️ Генерация данных для источника B...")
        df_b = generate_data(n_b, mu, sigma, deg_type_b, deg_start_b, deg_val_b)
        load_to_sqlite(df_b, SQLITE_PATH)

        st.write("⚙️ Генерация данных для источника C...")
        df_c = generate_data(n_c, mu, sigma, deg_type_c, deg_start_c, deg_val_c)
        load_to_csv(df_c, CSV_PATH)

        st.write("🤖 Запуск агентов...")
        status_dict = {"a": "⏳ работает", "b": "⏳ работает", "c": "⏳ работает"}

        t_a = threading.Thread(target=run_agent_a, args=(window_size, delay, selected_a, status_dict))
        t_b = threading.Thread(target=run_agent_b, args=(window_size, delay, selected_b, status_dict))
        t_c = threading.Thread(target=run_agent_c, args=(window_size, delay, selected_c, status_dict))

        t_a.start()
        t_b.start()
        t_c.start()

        # Прогресс-бар пока агенты работают
        total_windows = max(n_a, n_b, n_c) // window_size
        progress = st.progress(0, text="Агенты отправляют данные...")
        placeholders = st.empty()

        step = 0
        while t_a.is_alive() or t_b.is_alive() or t_c.is_alive():
            step = min(step + 1, total_windows)
            progress.progress(step / total_windows,
                               text=f"Обработано окон: ~{step}/{total_windows}")
            placeholders.markdown(
                f"- Источник A: {status_dict['a']}\n"
                f"- Источник B: {status_dict['b']}\n"
                f"- Источник C: {status_dict['c']}"
            )
            time.sleep(delay + 0.1)

        t_a.join()
        t_b.join()
        t_c.join()

        progress.progress(1.0, text="Готово!")
        placeholders.markdown(
            f"- Источник A: {status_dict['a']}\n"
            f"- Источник B: {status_dict['b']}\n"
            f"- Источник C: {status_dict['c']}"
        )
        status.update(label="✅ Эксперимент завершён!", state="complete")

    st.success("Данные отправлены. Переходи на Дашборд чтобы посмотреть результаты!")
    st.balloons()