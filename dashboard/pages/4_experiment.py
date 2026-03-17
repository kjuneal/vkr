import streamlit as st
import threading
import time
import numpy as np
import pandas as pd
import sqlite3
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import reset_experiment
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, text

# ── Константы ─────────────────────────────────────────────────────────────

SERVER_URL  = "http://127.0.0.1:8000"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH    = os.path.join(ROOT, "data", "source_c.csv")
SQLITE_PATH = os.path.join(ROOT, "source_b.db")
PG_DB_NAME  = "source_a.db" 

# ── Генераторы данных ──────────────────────────────────────────────────────

def generate_data(n, mu, sigma, degradation, deg_start, deg_value):
    values = np.random.normal(mu, sigma, n)

    if degradation == "mean_shift" and deg_start < n:
        values[deg_start:] += deg_value

    elif degradation == "variance" and deg_start < n:
        extra = np.random.normal(0, deg_value, n - deg_start)
        values[deg_start:] += extra

    elif degradation == "missing":
        # missing применяется агентом через NaN
        missing_idx = np.random.choice(
            range(deg_start, n),
            size=int((n - deg_start) * deg_value),
            replace=False
        )
        values[missing_idx] = np.nan

    timestamps = pd.date_range("2026-01-01", periods=n, freq="min")
    return pd.DataFrame({"timestamp": timestamps, "value": values})


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

def run_agent_a(window_size, delay, status_dict):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ["PGCLIENTENCODING"] = "UTF8"
    from agents.agent_a import AgentA
    try:
        agent = AgentA(PG_DB_NAME, SERVER_URL, window_size, delay)
        agent.run()
        status_dict["a"] = "✅ завершён"
    except Exception as e:
        status_dict["a"] = f"❌ ошибка: {e}"


def run_agent_b(window_size, delay, status_dict):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from agents.agent_b import AgentB
    try:
        agent = AgentB(SQLITE_PATH, SERVER_URL, window_size, delay)
        agent.run()
        status_dict["b"] = "✅ завершён"
    except Exception as e:
        status_dict["b"] = f"❌ ошибка: {e}"


def run_agent_c(window_size, delay, status_dict):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from agents.agent_c import AgentC
    try:
        agent = AgentC(CSV_PATH, SERVER_URL, window_size, delay)
        agent.run()
        status_dict["c"] = "✅ завершён"
    except Exception as e:
        status_dict["c"] = f"❌ ошибка: {e}"

# ── Интерфейс ──────────────────────────────────────────────────────────────

st.title("🧪 Управление экспериментом")
st.caption("Настройте параметры, нажмите «Начать» — система сгенерирует данные и запустит агентов")

st.divider()

# Общие параметры
st.subheader("⚙️ Общие параметры")
col1, col2, col3 = st.columns(3)
with col1:
    mu = st.number_input(
        "Базовое среднее (μ)", value=100.0, step=1.0,
        help="Ожидаемое среднее значение данных в нормальном режиме. "
             "Например, 100 означает что данные будут генерироваться около этого значения."
    )
with col2:
    sigma = st.number_input(
        "Базовое стд. откл. (σ)", value=5.0, step=0.5, min_value=0.1,
        help="Разброс данных в нормальном режиме. Чем больше σ, тем шире разброс. "
             "Рекомендуется: 3–10 для наглядного эксперимента."
    )
with col3:
    window_size = st.number_input(
        "Размер окна агента", value=20, step=5, min_value=5,
        help="Сколько записей обрабатывает агент за один цикл. "
             "По этому окну вычисляются метрики (среднее, стд. откл., полнота). "
             "Меньше окно — больше точек на графике, но больше шума."
    )

col4, _ = st.columns(2)
with col4:
    delay = st.number_input(
        "Задержка между окнами (сек)", value=1, step=1, min_value=0,
        help="Пауза между отправками метрик агентом. "
             "0 — максимальная скорость, 2–3 — удобно наблюдать в реальном времени."
    )
st.divider()

# Параметры источников
st.subheader("📦 Источник A — PostgreSQL (рост дисперсии)")
col1, col2, col3 = st.columns(3)
with col1:
    n_a = st.number_input(
        "Записей в источнике A", value=200, step=50, min_value=50,
        help="Общее количество строк в таблице. "
             "Рекомендуется минимум 100 для корректной фазы I SPC + записи с деградацией."
    )
with col2:
    deg_start_a = st.number_input(
        "Начало деградации (запись №)", value=100, step=10,
        min_value=0, max_value=n_a - 1, key="deg_a",
        help="С какой записи начинается рост дисперсии. "
             "Записи до этого момента используются системой для обучения (фаза I). "
             "Рекомендуется: не менее 5 × размер окна."
    )
with col3:
    deg_val_a = st.number_input(
        "Доп. σ при росте дисперсии", value=10.0, step=1.0, min_value=0.0,
        help="Насколько увеличится разброс данных после начала деградации. "
             "Например, 10 означает что стандартное отклонение вырастет с базового σ до σ+10. "
             "Рекомендуется: 0.5σ–2σ для постепенного роста, >2σ для резкого."
    )
st.divider()

st.subheader("📦 Источник B — SQLite (пропуски)")
col1, col2, col3 = st.columns(3)
with col1:
    n_b = st.number_input(
        "Записей в источнике B", value=200, step=50, min_value=50,
        help="Общее количество строк. Аналогично источнику A."
    )
with col2:
    deg_start_b = st.number_input(
        "Начало деградации (запись №)", value=100, step=10,
        min_value=0, max_value=n_b - 1, key="deg_b",
        help="С какой записи начинают появляться пропущенные значения (NULL). "
             "До этой записи данные полные (полнота = 1.0)."
    )
with col3:
    deg_val_b = st.slider(
        "Доля пропусков", min_value=0.0, max_value=0.5, value=0.2, step=0.05,
        help="Какая доля записей будет содержать пропуски после начала деградации. "
             "0.05 = 5% пропусков (лёгкая деградация), "
             "0.20 = 20% (умеренная), "
             "0.50 = 50% (критическая)."
    )
st.divider()

st.subheader("📦 Источник C — CSV (сдвиг среднего)")
col1, col2, col3 = st.columns(3)
with col1:
    n_c = st.number_input(
        "Записей в источнике C", value=200, step=50, min_value=50,
        help="Общее количество строк. Аналогично источнику A."
    )
with col2:
    deg_start_c = st.number_input(
        "Начало деградации (запись №)", value=100, step=10,
        min_value=0, max_value=n_c - 1, key="deg_c",
        help="С какой записи среднее значение начнёт смещаться. "
             "До этой записи данные генерируются с базовым μ."
    )
with col3:
    deg_val_c = st.number_input(
        "Величина сдвига (Δ)", value=20.0, step=5.0,
        help="На сколько единиц сдвинется среднее после начала деградации. "
             "Например, при μ=100 и Δ=20 среднее станет ~120. "
             "Рекомендуется: 1σ–2σ для постепенного, >3σ для мгновенного обнаружения."
    )

# Кнопка запуска
if st.button("🚀 Начать эксперимент", type="primary", use_container_width=True):

    # 1. Очищаем старые данные
    with st.status("Подготовка...", expanded=True) as status:

        st.write("🗑️ Очистка старых данных в БД...")
        result = reset_experiment()
        if "error" in result:
            st.error(f"Ошибка очистки: {result['error']}")
            st.stop()

        # 2. Генерация данных
        st.write("⚙️ Генерация данных для источника A...")
        df_a = generate_data(n_a, mu, sigma, "variance",   deg_start_a, deg_val_a)
        load_to_postgres(df_a, PG_DB_NAME)

        st.write("⚙️ Генерация данных для источника B...")
        df_b = generate_data(n_b, mu, sigma, "missing",    deg_start_b, deg_val_b)
        load_to_sqlite(df_b, SQLITE_PATH)

        st.write("⚙️ Генерация данных для источника C...")
        df_c = generate_data(n_c, mu, sigma, "mean_shift", deg_start_c, deg_val_c)
        load_to_csv(df_c, CSV_PATH)

        st.write("🤖 Запуск агентов...")
        status_dict = {"a": "⏳ работает", "b": "⏳ работает", "c": "⏳ работает"}

        t_a = threading.Thread(target=run_agent_a, args=(window_size, delay, status_dict))
        t_b = threading.Thread(target=run_agent_b, args=(window_size, delay, status_dict))
        t_c = threading.Thread(target=run_agent_c, args=(window_size, delay, status_dict))

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