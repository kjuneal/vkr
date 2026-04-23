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

import pandas as pd
from pathlib import Path
import subprocess
from datetime import datetime
import time as time_module
import re
import subprocess


def read_uploaded_df(uploaded_file):
    if uploaded_file is None:
        return None
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif name.endswith('.xlsx') or name.endswith('.xls'):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError('Unsupported file format')
    required = {'timestamp', 'value'}
    if not required.issubset(df.columns):
        raise ValueError('File must contain columns: timestamp, value')
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df[['timestamp', 'value']]

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
    df = df.reset_index(drop=True)
    df.to_sql("data", engine, index=False, if_exists="replace")


def load_to_sqlite(df, path):
    conn = sqlite3.connect(path)
    df = df.reset_index(drop=True)
    df.to_sql("data", conn, index=False, if_exists="replace")
    conn.close()


def load_to_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = df.reset_index(drop=True)
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

st.subheader("📥 Источник данных")
data_mode = st.radio(
    "Выберите режим подготовки данных",
    ["Синтетические данные", "Загруженные данные из файла", "Живой мониторинг пинга"],
    horizontal=True
)

external_mode = data_mode == "Загруженные данные из файла"

selected_a, selected_b, selected_c = [], [], []
window_size, delay = 20, 0
df_a, df_b, df_c = None, None, None


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

# Список хостов
HTTP_HOSTS = {
    "🇺🇸 Google": "https://www.google.com",
    "☁️ Cloudflare": "https://1.1.1.1",
    "🇷🇺 Yandex": "https://yandex.ru", 
    "📱 VK": "https://vk.com",
    "🐧 GitHub": "https://github.com"
}

import requests

def http_check(url):
    """🎯 Мониторит Response Time + Size страницы"""
    try:
        start = time_module.time()
        response = requests.get(url, timeout=5)
        elapsed = (time_module.time() - start) * 1000  # ms
        
        size_kb = len(response.content) / 1024  # KB
        
        print(f"✅ {url}: {elapsed:.1f}ms, {size_kb:.0f}KB, status={response.status_code}")
        return elapsed  # Возвращаем время ответа!
        
    except Exception as e:
        print(f"❌ {url}: {e}")
        return float('nan')
    
def live_agent_loop(source_key, url, csv_path, stop_event, window_size, interval, selected_metrics):
    """
    Один поток на источник:
    1. Опрашивает URL каждые interval секунд
    2. Пишет результат в CSV
    3. Когда накопилось window_size новых записей — считает метрики и отправляет на сервер
    """
    import sys, os
    sys.path.insert(0, ROOT)
    os.environ["PGCLIENTENCODING"] = "UTF8"

    from agents.base_agent import BaseAgent, compute_metrics
    import pandas as pd
    import numpy as np

    agent = BaseAgent(SERVER_URL)
    csv_path.parent.mkdir(exist_ok=True)

    buffer = []        # накапливаем записи до размера окна
    sent_windows = 0

    while not stop_event.is_set():
        # 1. Опрашиваем хост
        latency = http_check(url)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        value = latency if not (isinstance(latency, float) and pd.isna(latency)) else float('nan')

        # 2. Пишем в CSV (общий лог)
        new_row = pd.DataFrame([{'timestamp': timestamp, 'value': value}])
        if csv_path.exists():
            new_row.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            new_row.to_csv(csv_path, index=False)

        # 3. Добавляем в буфер
        buffer.append(value)

        # 4. Когда буфер заполнен — считаем метрики и отправляем
        if len(buffer) >= window_size:
            series = pd.Series(buffer)
            metrics = compute_metrics(series, selected_metrics)

            source_name = f"source_{source_key}"
            agent.send_metrics(source_name, metrics)

            sent_windows += 1
            print(f"[Live {source_key.upper()}] окно {sent_windows}: {metrics}")

            buffer = []  # сбрасываем буфер

        # 5. Ждём до следующего опроса
        time_module.sleep(interval)

# ─── ПИНГ ФУНКЦИИ ───
def ping_once(host="8.8.8.8"):
    try:
        result = subprocess.run(
            ['ping', '-n', '1', '-w', '3000', host],
            capture_output=True, text=True, timeout=5,
            encoding='cp866'  # Русская кодировка Windows!
        )
        
        output = result.stdout.lower()
        print(f"DEBUG {host}: {output[:150]}")  # Смотрим в терминале!
        
        if result.returncode == 0:
            # 5 вариантов парсинга
            patterns = [
                r'время[ =<]([\d,]+)',  # время=25
                r'time[ =<]([\d,]+)',   # time=25ms
                r'врем[я=]\s*([\d,]+)', # время<1
                r'(\d+)[ ,]мс',         # 25мс
                r'avg[ /=]*([\d,]+)'    # avg / 25
            ]
            
            for pattern in patterns:
                match = re.search(pattern, output)
                if match:
                    latency = float(match.group(1).replace(',', '.'))
                    print(f"✅ {host}: {latency:.1f}ms")
                    return latency
            
            print(f"❌ {host}: паттерны не сработали")
        
    except Exception as e:
        print(f"❌ {host}: {e}")
    
    return float('nan')

def ping_loop(host, csv_path, stop_event, interval=2):
    csv_path.parent.mkdir(exist_ok=True)
    
    while not stop_event.is_set():
        try:
            latency = http_check(host) #latency = ping_once(host)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            new_row = pd.DataFrame([{
                'timestamp': timestamp,
                'value': latency if not pd.isna(latency) else float('nan')
            }])
            
            if csv_path.exists():
                new_row.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                new_row.to_csv(csv_path, index=False)
        except Exception as e:
            print(f"ping_loop error: {e}")
        time_module.sleep(interval)

def metrics_block(source_key, default_metrics, disabled=False):
    return st.multiselect(
        f'Метрики источника {source_key.upper()}',
        options=list(ALL_METRICS.keys()),
        default=st.session_state.get(f'sel_{source_key}', default_metrics),
        format_func=lambda x: ALL_METRICS[x],
        key=f'sel_{source_key}',
        disabled=disabled,
    )


def file_block(source_key):
    uploaded = st.file_uploader(
        f'Файл для источника {source_key.upper()}',
        type=['csv', 'xlsx', 'xls'],
        key=f'file_{source_key}',
    )
    df = None
    if uploaded is not None:
        try:
            df = read_uploaded_df(uploaded)
            st.success(f'Загружен файл: {uploaded.name}')
            st.dataframe(df.head(10))
        except Exception as e:
            st.error(f'Ошибка загрузки источника {source_key.upper()}: {e}')
    return df

st.divider()

# if data_mode == "Живой мониторинг пинга":
#     st.markdown("---")

#     # Инициализация состояния
#     if 'monitoring_active' not in st.session_state:
#         st.session_state.monitoring_active = False
#         st.session_state.agents_started = False
#         st.session_state.agent_status = {"a": "⏳ не запущен", "b": "⏳ не запущен", "c": "⏳ не запущен"}
#         st.session_state.windows_processed = {"a": 0, "b": 0, "c": 0}
#         st.session_state.ping_threads = {}
#         st.session_state.stop_events = {}
    
#     # 3 источника с настройками
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.markdown("### 📦 Источник A")
#         host_a = st.selectbox("Хост A", options=list(HTTP_HOSTS.keys()), 
#                             format_func=lambda x: f"{x} ({HTTP_HOSTS[x]})", key="host_a")
#         metrics_a = metrics_block('a', ['mean', 'std'])

#     with col2:
#         st.markdown("### 📦 Источник B") 
#         host_b = st.selectbox("Хост B", options=list(HTTP_HOSTS.keys()), 
#                             format_func=lambda x: f"{x} ({HTTP_HOSTS[x]})", key="host_b")
#         metrics_b = metrics_block('b', ['completeness', 'iqr'])

#     with col3:
#         st.markdown("### 📦 Источник C")
#         host_c = st.selectbox("Хост C", options=list(HTTP_HOSTS.keys()), 
#                             format_func=lambda x: f"{x} ({HTTP_HOSTS[x]})", key="host_c")
#         metrics_c = metrics_block('c', ['mean', 'std'])

#     # 
#     window_size = st.number_input("Размер окна агента", value=20, min_value=5, key="live_window")
#     delay = st.number_input("Задержка агентов (сек)", value=0, min_value=0, key="live_delay")

#     # Пути к файлам
#     csv_paths = {
#         'a': Path("data/ping_a_live.csv"),
#         'b': Path("data/ping_b_live.csv"), 
#         'c': Path("data/ping_c_live.csv")
#     }
#     st.session_state.csv_paths = csv_paths

    

#     # # Инициализация потоков
#     # if 'ping_threads' not in st.session_state:
#     #     st.session_state.ping_threads = {}
#     #     st.session_state.stop_events = {}
#     #     st.session_state.csv_paths = {
#     #         'a': Path("data/ping_a_live.csv"),
#     #         'b': Path("data/ping_b_live.csv"), 
#     #         'c': Path("data/ping_c_live.csv")
#     #     }

#     # Кнопки управления
#     col_btn1, col_btn2, col_clear = st.columns([2,2,1])

    
#     with col_btn1:
#         if st.button("🚀 Запустить мониторинг всех хостов", type="primary", disabled=st.session_state.monitoring_active):
#             # Очистка старых файлов
#             for source in ['a', 'b', 'c']:
#                 csv_path = st.session_state.csv_paths[source]
#                 if csv_path.exists():
#                     csv_path.unlink()
            
#             #запуск потоков
#             for source, host_name in [('a', host_a), ('b', host_b), ('c', host_c)]:
#                 csv_path = st.session_state.csv_paths[source]
                
#                 # Останавливаем старый поток если есть
#                 if source in st.session_state.stop_events:
#                     st.session_state.stop_events[source].set()
                
#                 # Создаём новый флаг и поток
#                 stop_event = threading.Event()
#                 st.session_state.stop_events[source] = stop_event
                
#                 thread = threading.Thread(
#                     target=ping_loop,
#                     args=(HTTP_HOSTS[host_name], csv_path, stop_event, 2),
#                     daemon=True
#                 )
#                 st.session_state.ping_threads[source] = thread
#                 thread.start()

#             st.session_state.monitoring_active = True
#             st.session_state.agents_started = False
#             st.success("🟢 Мониторинг запущен! Данные собираются каждые 2 секунды.")
#             st.rerun()

#     with col_btn2:
#         if st.button("⏹️ Остановить все потоки", disabled=not st.session_state.monitoring_active):
#             for source in ['a', 'b', 'c']:
#                 if source in st.session_state.get('stop_events', {}):
#                     st.session_state.stop_events[source].set()
#             st.session_state.monitoring_active = False
#             st.success("🛑 Мониторинг остановлен!")
#             st.rerun()

#     with col_clear: 
#         if st.button("🗑️ Очистить файлы", type="secondary"):
#             for source in ['a','b','c']:
#                 if source in st.session_state.get('stop_events', {}):
#                     st.session_state.stop_events[source].set()
#                 csv_path = csv_paths[source]
#                 if csv_path.exists():
#                     csv_path.unlink()
#             st.session_state.monitoring_active = False
#             st.session_state.agents_started = False
#             st.session_state.ping_threads = {}
#             st.session_state.stop_events = {}
#             st.success("🗑️ Файлы очищены и мониторинг остановлен!")
#             st.rerun()

#     # Статус всех источников
#     st.markdown("### 📊 Статус сбора данных")
#     status_cols = st.columns(3)
    
#     total_points = 0
#     ready_for_agents = True
    
#     for i, source in enumerate(['a','b','c']):
#         csv_path = st.session_state.csv_paths[source]
#         with status_cols[i]:
#             if csv_path.exists():
#                 try:
#                     df = pd.read_csv(csv_path)
#                     count = len(df)
#                     valid_count = len(df.dropna(subset=['value']))
#                     total_points += count
#                     latest = df['value'].iloc[-1] if len(df) > 0 else float('nan')
                    
#                     st.metric(f"📦 {source.upper()}", f"{count} точек", f"{valid_count}/{count}")
#                     st.text(f"Последняя: {latest:.1f}ms")
#                     st.line_chart(df.set_index('timestamp')['value'], height=150)
                    
#                     if count < 30:
#                         ready_for_agents = False
                        
#                 except Exception as e:
#                     st.metric(f"📦 {source.upper()}", "Ошибка файла", "❌")
#                     st.error(f"{e}")
#                     ready_for_agents = False
#             else:
#                 st.metric(f"📦 {source.upper()}", "0 точек", "⏳ ждём...")
#                 ready_for_agents = False

#     # if st.session_state.monitoring_active:
#     #     col_refresh, col_status = st.columns([1, 3])
#     #     with col_refresh:
#     #         if st.button("🔄 Обновить сейчас", key="refresh_live"):
#     #             st.rerun()
#     #     with col_status:
#     #         st.info(f"📊 Точек: **{total_points}/90** | Агенты: {'✅ готовы' if total_points>=90 else '⏳ собираем'}")

#     # КНОПКА "Обновить" с копированием и агентами
#     col_manual, col_progress = st.columns([3, 1])
#     with col_progress:
#         if st.button("🔄 Обновить и запустить агентов", disabled=st.session_state.agents_started):
#             st.session_state.force_agent_run = True

#     # Логика запуска агентов (каждый раз при force_agent_run)
#     if (st.session_state.monitoring_active and 
#         total_points >= 30 and 
#         (st.session_state.get('force_agent_run', False) or 
#         (not st.session_state.agents_started and total_points >= 90))):

#         st.markdown("### 🤖 Запуск агентов...")
        
#         # КОПИРУЕМ НОВЫЕ ДАННЫЕ В БД (каждый раз!)
#         with st.status("📤 Копирование свежих данных...", expanded=False):
#             for source in ['a','b','c']:
#                 csv_path = st.session_state.csv_paths[source]
#                 if csv_path.exists():
#                     df_live = pd.read_csv(csv_path)
#                     print(f"DEBUG: копирую {len(df_live)} точек из {csv_path}")
#                     if source == 'a':
#                         load_to_postgres(df_live, PG_DB_NAME)
#                     elif source == 'b':
#                         load_to_sqlite(df_live, SQLITE_PATH)
#                     else:
#                         load_to_csv(df_live, CSV_PATH)
    
#         # Запуск агентов
#         status_dict = {"a": "⏳", "b": "⏳", "c": "⏳"}
#         t_a = threading.Thread(target=run_agent_a, args=(window_size, 0, metrics_a, status_dict))
#         t_b = threading.Thread(target=run_agent_b, args=(window_size, 0, metrics_b, status_dict))
#         t_c = threading.Thread(target=run_agent_c, args=(window_size, 0, metrics_c, status_dict))
        
#         t_a.start(); t_b.start(); t_c.start()
        
#         progress = st.progress(0)
#         step = 0
#         while any([t_a.is_alive(), t_b.is_alive(), t_c.is_alive()]):
#             step += 1
#             progress.progress(min(1.0, step/20))
#             time.sleep(0.5)
        
#         t_a.join(); t_b.join(); t_c.join()
        
#         st.success(f"✅ Агенты обновили дашборд! Окна: A={status_dict['a']}, B={status_dict['b']}, C={status_dict['c']}")
        
#         if st.session_state.get('force_agent_run'):
#             del st.session_state.force_agent_run
#         st.session_state.agents_started = True
#         st.rerun()

#     # автозапуск агентов
#     if (st.session_state.monitoring_active and 
#     total_points >= 90 and 
#     not st.session_state.agents_started and 
#     ready_for_agents):

#         st.markdown("### 🤖 🚀 АВТОЗАПУСК АГЕНТОВ")
#         st.success("✅ 90+ точек! Копирую данные и запускаю агентов...")
        
#         # Копируем в основные источники
#         with st.status("📤 Загрузка в PostgreSQL/SQLite/CSV...", expanded=True):
#             for source in ['a','b','c']:
#                 csv_path = st.session_state.csv_paths[source]
#                 if csv_path.exists():
#                     df_live = pd.read_csv(csv_path)
#                     if source == 'a':
#                         load_to_postgres(df_live, PG_DB_NAME)
#                     elif source == 'b':
#                         load_to_sqlite(df_live, SQLITE_PATH)
#                     else:
#                         load_to_csv(df_live, CSV_PATH)
#                     st.write(f"✅ {source.upper()}: {len(df_live)} точек загружено")

#         # Запуск агентов
#         st.session_state.agents_started = True
#         status_dict = {"a": "⏳ запускается", "b": "⏳ запускается", "c": "⏳ запускается"}
        
#         t_a = threading.Thread(target=run_agent_a, args=(window_size, st.session_state.live_delay, metrics_a, status_dict))
#         t_b = threading.Thread(target=run_agent_b, args=(window_size, st.session_state.live_delay, metrics_b, status_dict))
#         t_c = threading.Thread(target=run_agent_c, args=(window_size, st.session_state.live_delay, metrics_c, status_dict))
        
#         t_a.start(); t_b.start(); t_c.start()
        
#         progress = st.progress(0, text="Агенты анализируют...")
#         step = 0
        
#         while any([t_a.is_alive(), t_b.is_alive(), t_c.is_alive()]):
#             step += 1
#             progress.progress(min(1.0, step/30))
#             time.sleep(0.5)  # Небольшая пауза
        
#         t_a.join(); t_b.join(); t_c.join()
#         status_dict.update({"a": "✅ завершён", "b": "✅ завершён", "c": "✅ завершён"})
#         progress.progress(1.0, text="✅ Агенты завершили анализ!")
        
#         st.balloons()
#         st.success("🎉 Live-данные на дашборде! Перейди посмотреть!")
#         st.rerun()

if data_mode == "Живой мониторинг пинга":

    # Инициализация состояния
    for key, default in [
        ('live_running', False),
        ('ping_threads', {}),
        ('stop_events', {}),
        ('csv_paths', {
            'a': Path("data/ping_a_live.csv"),
            'b': Path("data/ping_b_live.csv"),
            'c': Path("data/ping_c_live.csv")
        }),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # Настройки
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📦 Источник A")
        host_a = st.selectbox("Хост A", options=list(HTTP_HOSTS.keys()),
                              format_func=lambda x: f"{x}", key="host_a")
        metrics_a = metrics_block('a', ['mean', 'std'])
    with col2:
        st.markdown("### 📦 Источник B")
        host_b = st.selectbox("Хост B", options=list(HTTP_HOSTS.keys()),
                              format_func=lambda x: f"{x}", key="host_b")
        metrics_b = metrics_block('b', ['mean', 'iqr'])
    with col3:
        st.markdown("### 📦 Источник C")
        host_c = st.selectbox("Хост C", options=list(HTTP_HOSTS.keys()),
                              format_func=lambda x: f"{x}", key="host_c")
        metrics_c = metrics_block('c', ['mean', 'std'])

    col_w, col_d = st.columns(2)
    with col_w:
        live_window = st.number_input(
            "Размер окна (записей)", value=10, min_value=3, key="live_window",
            help="Когда накопится столько записей — агент считает метрики и отправляет на сервер"
        )
    with col_d:
        live_interval = st.number_input(
            "Интервал опроса (сек)", value=3, min_value=1, key="live_interval",
            help="Как часто опрашивать каждый хост"
        )

    st.divider()

    # Кнопки управления
    col_start, col_stop, col_clear = st.columns([2, 2, 1])
    with col_start:
        start_clicked = st.button(
            "🚀 Начать мониторинг",
            type="primary",
            disabled=st.session_state.live_running,
            use_container_width=True
        )
    with col_stop:
        stop_clicked = st.button(
            "⏹️ Остановить",
            disabled=not st.session_state.live_running,
            use_container_width=True
        )
    with col_clear:
        clear_clicked = st.button("🗑️ Сбросить", use_container_width=True)

    if clear_clicked:
        # Останавливаем всё
        for src in ['a', 'b', 'c']:
            if src in st.session_state.stop_events:
                st.session_state.stop_events[src].set()
        for path in st.session_state.csv_paths.values():
            if path.exists():
                path.unlink()
        # Очищаем БД
        reset_experiment()
        st.session_state.live_running = False
        st.session_state.ping_threads = {}
        st.session_state.stop_events = {}
        st.success("Сброшено!")
        st.rerun()

    if stop_clicked:
        for src in ['a', 'b', 'c']:
            if src in st.session_state.stop_events:
                st.session_state.stop_events[src].set()
        st.session_state.live_running = False
        st.rerun()

    if start_clicked:
        # Очищаем старые файлы и БД
        for path in st.session_state.csv_paths.values():
            if path.exists():
                path.unlink()
        reset_experiment()

        hosts = {'a': HTTP_HOSTS[host_a], 'b': HTTP_HOSTS[host_b], 'c': HTTP_HOSTS[host_c]}
        metrics_map = {'a': metrics_a, 'b': metrics_b, 'c': metrics_c}

        for src in ['a', 'b', 'c']:
            # Останавливаем старый поток
            if src in st.session_state.stop_events:
                st.session_state.stop_events[src].set()

            stop_event = threading.Event()
            st.session_state.stop_events[src] = stop_event

            # Один поток делает всё: опрос → накопление → метрики → сервер
            t = threading.Thread(
                target=live_agent_loop,
                args=(
                    src,
                    hosts[src],
                    st.session_state.csv_paths[src],
                    stop_event,
                    live_window,
                    live_interval,
                    metrics_map[src],
                ),
                daemon=True
            )
            st.session_state.ping_threads[src] = t
            t.start()

        st.session_state.live_running = True
        st.rerun()

    # Дашборд статуса — обновляется при каждом рендере
    if st.session_state.live_running or any(
        st.session_state.csv_paths[s].exists() for s in ['a', 'b', 'c']
    ):
        st.markdown("### 📊 Данные в реальном времени")
        cols = st.columns(3)
        for i, src in enumerate(['a', 'b', 'c']):
            path = st.session_state.csv_paths[src]
            with cols[i]:
                if path.exists():
                    try:
                        df_live = pd.read_csv(path)
                        n = len(df_live)
                        valid = df_live['value'].notna().sum()
                        last = df_live['value'].dropna().iloc[-1] if valid > 0 else float('nan')
                        windows_sent = n // live_window

                        st.metric(
                            f"Источник {src.upper()}",
                            f"{n} записей",
                            f"отправлено окон: {windows_sent}"
                        )
                        if not pd.isna(last):
                            st.caption(f"Последний запрос: {last:.1f} мс")
                        if n > 1:
                            st.line_chart(
                                df_live.set_index('timestamp')['value'].dropna(),
                                height=150
                            )
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.metric(f"Источник {src.upper()}", "0 записей", "ждём...")

        if st.session_state.live_running:
            st.info("🔴 Мониторинг активен. Обновите страницу чтобы увидеть свежие данные, или нажмите кнопку ниже.")
            if st.button("🔄 Обновить данные"):
                st.rerun()


# --- РЕЖИМ ГЕНЕРАЦИИ ДАННЫХ ---
elif data_mode == 'Синтетические данные':
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

    # Параметры источников
    st.subheader("📦 Источник A — PostgreSQL")
    col1, col2 = st.columns(2)
    with col1:
        n_a = st.number_input(
            "Записей в источнике A", step=50, min_value=50,
            value=st.session_state.get("n_a", 500),
            key="n_a", disabled=external_mode,
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
            ), disabled=external_mode,
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
                "Рекомендуется: не менее 5 × размер окна.", disabled=external_mode or (deg_type_a == "none")
        )
    with col4:
        param_label, param_help, param_default = DEG_PARAM_HELP[deg_type_a]
        if deg_type_a == "none":
            deg_val_a = 0.0
            st.number_input(param_label if deg_type_a != "none" else "Параметр", value=0.0, disabled=True)
        else:
            deg_val_a = st.number_input(param_label, value=param_default, step=0.1, help=param_help, key="deg_val_a", disabled=external_mode)

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
            key="n_b", disabled=external_mode,
            help="Общее количество строк. Аналогично источнику A."
        )
    with col2:
        deg_type_b = st.selectbox(
            "Вид деградации",
            options=list(DEGRADATION_OPTIONS.keys()),
            format_func=lambda x: DEGRADATION_OPTIONS[x],
            index=list(DEGRADATION_OPTIONS.keys()).index(
                st.session_state.get("deg_type_b", "none")
            ), disabled=external_mode,
            key="deg_type_b"
        )
    col3, col4 = st.columns(2)
    with col3:
        deg_start_b = st.number_input(
            "Начало деградации (запись №)", step=10,
            min_value=0, max_value=n_b - 1, key="deg_start_b",
            value=st.session_state.get("deg_start_b", 200), 
            help="С какой записи начинают появляться пропущенные значения (NULL). "
                "До этой записи данные полные (полнота = 1.0).", disabled=external_mode or (deg_type_b == "none")
        )
    with col4:
        param_label, param_help, param_default = DEG_PARAM_HELP[deg_type_b]
        if deg_type_b == "none":
            deg_val_b = 0.0
            st.number_input("Параметр", value=0.0, disabled=True, key="val_b_dis")
        else:
            deg_val_b = st.number_input(param_label, value=param_default, step=0.1, help=param_help, key="deg_val_b", disabled=external_mode)
            
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
            key="n_c", disabled=external_mode,
            help="Общее количество строк. Аналогично источнику A."
        )
    with col2:
        deg_type_c = st.selectbox(
            "Вид деградации",
            options=list(DEGRADATION_OPTIONS.keys()),
            format_func=lambda x: DEGRADATION_OPTIONS[x],
            index=list(DEGRADATION_OPTIONS.keys()).index(
                st.session_state.get("deg_type_c", "none")
            ), disabled=external_mode,
            key="deg_type_c"
        )
    col3, col4 = st.columns(2)   
    with col3:
        deg_start_c = st.number_input(
            "Начало деградации (запись №)", step=10,
            min_value=0, max_value=n_c - 1, key="deg_start_c",
            value=st.session_state.get("deg_start_c", 200), 
            help="С какой записи среднее значение начнёт смещаться. "
                "До этой записи данные генерируются с базовым μ.", disabled=external_mode or (deg_type_c == "none")
        )
    with col4:
        param_label, param_help, param_default = DEG_PARAM_HELP[deg_type_c]
        if deg_type_c == "none":
            deg_val_c = 0.0
            st.number_input("Параметр", value=0.0, disabled=True, key="val_c_dis")
        else:
            deg_val_c = st.number_input(param_label, value=param_default, step=0.1, help=param_help, key="deg_val_c", disabled=external_mode)


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

# РЕЖИМ ЗАГРУЗКИ ДАННЫХ
else:
    st.subheader('⚙️ Параметры агентов')
    col1, col2 = st.columns(2)
    with col1:
        window_size = st.number_input('Размер окна агента', step=5, min_value=5, value=st.session_state.get('window_size', 20), key='window_size')
    with col2:
        delay = st.number_input('Задержка между окнами (сек)', step=1, min_value=0, value=st.session_state.get('delay', 0), key='delay')

    st.divider()
    st.subheader('📦 Источник A — PostgreSQL')
    df_a = file_block('a')
    selected_a = metrics_block('a', ['mean'])
    st.divider()

    st.subheader('📦 Источник B — SQLite')
    df_b = file_block('b')
    selected_b = metrics_block('b', ['mean'])
    st.divider()

    st.subheader('📦 Источник C — CSV')
    df_c = file_block('c')
    selected_c = metrics_block('c', ['mean'])

# Кнопка запуска
if data_mode in ["Синтетические данные", "Загруженные данные из файла"]:
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
                'mode': data_mode,
                'window_size': window_size,
                'delay': delay,
                'sources': {
                    'source_a': {'metrics': selected_a, 'label': 'A'},
                    'source_b': {'metrics': selected_b, 'label': 'B'},
                    'source_c': {'metrics': selected_c, 'label': 'C'},
                }
            }
            if data_mode == 'Синтетические данные':
                config['mu'] = mu
                config['sigma'] = sigma
                config['sources']['source_a'].update({'n': n_a, 'degradation': deg_type_a, 'deg_start': deg_start_a, 'deg_value': deg_val_a, 'label': DEGRADATION_OPTIONS[deg_type_a]})
                config['sources']['source_b'].update({'n': n_b, 'degradation': deg_type_b, 'deg_start': deg_start_b, 'deg_value': deg_val_b, 'label': DEGRADATION_OPTIONS[deg_type_b]})
                config['sources']['source_c'].update({'n': n_c, 'degradation': deg_type_c, 'deg_start': deg_start_c, 'deg_value': deg_val_c, 'label': DEGRADATION_OPTIONS[deg_type_c]})
            else:
                if df_a is None or df_b is None or df_c is None:
                    st.error('Загрузите файлы для всех трёх источников')
                    st.stop()
                config['sources']['source_a']['file'] = 'uploaded'
                config['sources']['source_b']['file'] = 'uploaded'
                config['sources']['source_c']['file'] = 'uploaded'
            save_experiment_config(config)

            # 2. Загрузка / генерация данных
            if data_mode == "Синтетические данные":
                st.write("⚙️ Генерация данных для источника A...")
                df_a = generate_data(n_a, mu, sigma, deg_type_a, deg_start_a, deg_val_a)
                load_to_postgres(df_a, PG_DB_NAME)

                st.write("⚙️ Генерация данных для источника B...")
                df_b = generate_data(n_b, mu, sigma, deg_type_b, deg_start_b, deg_val_b)
                load_to_sqlite(df_b, SQLITE_PATH)

                st.write("⚙️ Генерация данных для источника C...")
                df_c = generate_data(n_c, mu, sigma, deg_type_c, deg_start_c, deg_val_c)
                load_to_csv(df_c, CSV_PATH)
            else:
                st.write("📄 Использование загруженного файла...")
                if df_a is None or df_b is None or df_c is None:
                    st.error("Загрузите файл для каждого источника: A, B и C")
                    st.stop()

                load_to_postgres(df_a, PG_DB_NAME)
                load_to_sqlite(df_b, SQLITE_PATH)
                load_to_csv(df_c, CSV_PATH)

            st.write("🤖 Запуск агентов...")
            status_dict = {"a": "⏳ работает", "b": "⏳ работает", "c": "⏳ работает"}

            t_a = threading.Thread(target=run_agent_a, args=(window_size, delay, selected_a, status_dict))
            t_b = threading.Thread(target=run_agent_b, args=(window_size, delay, selected_b, status_dict))
            t_c = threading.Thread(target=run_agent_c, args=(window_size, delay, selected_c, status_dict))

            t_a.start()
            t_b.start()
            t_c.start()

            # Прогресс-бар работы агентов
            if data_mode == "Синтетические данные":
                total_windows = max(n_a, n_b, n_c) // window_size
            else:
                total_windows = max(len(df_a), len(df_b), len(df_c)) // window_size
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

        st.success("Данные отправлены. Перейдите на Дашборд, чтобы посмотреть результаты!")
        st.balloons()