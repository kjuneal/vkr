"""
Batch-скрипт для запуска экспериментальных серий.

Использование:
    python -m experiments.run_experiments --series 1
    python -m experiments.run_experiments --series 2 --replications 30
    python -m experiments.run_experiments --series all
    python -m experiments.run_experiments --series 1 --quick   # 5 повторений вместо 30 для проверки

Скрипт:
  1. Открывает соединение с experiments_db (отдельная БД, не UI).
  2. Перед запуском серии — очищает spc_state и spc_event (внутри серии данные сохраняются).
  3. Для каждого сценария × каждой репликации:
     - генерирует синтетический ряд с фиксированным seed (воспроизводимо);
     - разбивает на окна, считает метрики;
     - прогоняет через update_spc() с уникальным run_id;
     - извлекает первое срабатывание каждого метода через get_first_event();
     - инкрементально пишет результат в CSV.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
np.random.seed(42)

import pandas as pd
from tqdm import tqdm

# Добавляем корень проекта в sys.path, чтобы импорты server.* работали
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import spc                                # SPC-движок и функции
from agents.base_agent import compute_metrics         # точно та же функция, что в агентах
from data_generate import generate_data               # генератор синтетических рядов

from experiments.db import SessionLocal, init_experiments_db
from experiments.experiments_config import ALL_SERIES, DEFAULT_BASELINE_SIZE


# ── Параметры по умолчанию ────────────────────────────────────────────────
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────
# Однократный прогон одной репликации одного сценария
# ─────────────────────────────────────────────────────────────────────────
def run_single_replication(
    db,
    series_name: str,
    scenario: dict,
    replication: int,
    baseline_size: int,
    seed: int,
) -> list[dict]:
    """
    Один прогон: генерирует ряд, прогоняет через SPC, возвращает результаты
    для каждого из трёх методов (Шухарт, CUSUM, EWMA) — список из 3 dict'ов.
    """
    # 1. Уникальный run_id для этого прогона
    run_id = f"{series_name}__{scenario['name']}__rep{replication:02d}"

    # 2. Воспроизводимая генерация данных
    np.random.seed(seed)

    df = generate_data(
        n=scenario["n_observations"],
        mu=scenario["mu"],
        sigma=scenario["sigma"],
        degradation=scenario["degradation"],
        deg_start=scenario["deg_start"] if scenario["deg_start"] is not None else scenario["n_observations"],
        deg_value=scenario["deg_value"],
    )

    # 3. Разбиение на окна и вычисление метрики
    window_size = scenario["window_size"]
    metric_name = scenario["metric"]

    n_total_windows = len(df) // window_size
    source = "exp_source"  # фиктивный источник, важно только различать в БД

    # 4. Истинный момент изменения в терминах окон фазы II
    # Записи 1..baseline_size*window_size — это фаза I (там SPC ничего не сигналит).
    # Деградация начинается с записи deg_start.
    # Окно номер k в ФАЗЕ II соответствует записям:
    #   (baseline_size + k - 1) * window_size + 1 ... (baseline_size + k) * window_size
    # Истинный момент изменения в окнах фазы II:
    if scenario["deg_start"] is None:
        true_change_step = None  # деградации нет (для серии 1)
    else:
        deg_start_idx = scenario["deg_start"]
        # окно (от 1) в общей нумерации, где впервые попадают деградированные данные
        first_degraded_window = (deg_start_idx // window_size) + 1
        # окно фазы II
        true_change_step = first_degraded_window - baseline_size
        if true_change_step < 1:
            true_change_step = 1  # деградация началась в фазе I — считаем что в начале фазы II

    # 5. Прогон через SPC
    for window_idx in range(n_total_windows):
        start = window_idx * window_size
        end   = start + window_size
        window_series = df["value"].iloc[start:end]

        metrics = compute_metrics(window_series, [metric_name])
        if metric_name in metrics:
            value = metrics[metric_name]
            spc.update_spc(
                db=db,
                source=source,
                metric_name=metric_name,
                new_value=value,
                run_id=run_id,
                baseline_size=baseline_size,
            )

    # 6. Сбор результатов: первое срабатывание каждого метода
    n_phase2_steps = max(0, n_total_windows - baseline_size)
    results = []
    for method in ("shewhart", "cusum", "ewma"):
        first_event = spc.get_first_event(
            db=db,
            run_id=run_id,
            source=source,
            metric_name=metric_name,
            method=method,
        )
        all_events = spc.get_events(
            db=db, run_id=run_id, source=source, metric_name=metric_name, method=method,
        )

        first_step = first_event.step if first_event else None
        signal_count = len(all_events)

        # Задержка обнаружения:
        #   - если деградации нет (серия 1): задержка = first_step (это и есть ARL₀)
        #   - если деградация есть и first_step >= true_change_step: задержка = first_step - true_change_step + 1
        #   - если first_step < true_change_step: ложное срабатывание ДО деградации
        #   - если first_step is None: метод не сработал вообще
        if first_step is None:
            detection_delay = None
            is_false_alarm  = False
        elif true_change_step is None:
            # серия 1 — все срабатывания ложные
            detection_delay = first_step
            is_false_alarm  = True
        elif first_step < true_change_step:
            detection_delay = None
            is_false_alarm  = True
        else:
            detection_delay = first_step - true_change_step + 1
            is_false_alarm  = False

        # mu_hat, sigma_hat для дебага — берём из первого события или из state
        state = spc.get_state(db=db, source=source, metric_name=metric_name, run_id=run_id)
        mu_hat = float(state.mu_hat) if state and state.mu_hat is not None else None
        sigma_hat = float(state.sigma_hat) if state and state.sigma_hat is not None else None

        results.append({
            "series":             series_name,
            "scenario":           scenario["name"],
            "replication":        replication,
            "run_id":             run_id,
            "source":             source,
            "metric":             metric_name,
            "method":             method,
            "true_change_step":   true_change_step,
            "first_signal_step":  first_step,
            "signal_count":       signal_count,
            "detection_delay":    detection_delay,
            "is_false_alarm":     is_false_alarm,
            "mu_hat":             mu_hat,
            "sigma_hat":          sigma_hat,
            "baseline_size":      baseline_size,
            "n_phase2_steps":     n_phase2_steps,
            "n_total_observations": scenario["n_observations"],
            "degradation":        scenario["degradation"],
            "deg_value":          scenario["deg_value"],
            "deg_start":          scenario["deg_start"],
            "seed":               seed,
        })

    return results


# ─────────────────────────────────────────────────────────────────────────
# Запуск целой серии
# ─────────────────────────────────────────────────────────────────────────
def run_series(series_key: str, replications_override: Optional[int] = None) -> Path:
    """
    Запустить одну серию. Возвращает путь к итоговому CSV.
    """
    series = ALL_SERIES[series_key]

    if not series["scenarios"]:
        print(f"[!] Серия {series_key} ({series['name']}) не имеет сценариев — пропускаем.")
        if "note" in series:
            print(f"    Примечание: {series['note']}")
        return None

    series_name = series["name"]
    base_baseline = series.get("baseline_size", DEFAULT_BASELINE_SIZE)
    n_repl = replications_override if replications_override is not None else series["replications"]

    print(f"\n{'═' * 75}")
    print(f"СЕРИЯ {series_key}: {series['description']}")
    print(f"  имя:           {series_name}")
    print(f"  сценариев:     {len(series['scenarios'])}")
    print(f"  повторений:    {n_repl}")
    print(f"  всего прогонов: {len(series['scenarios']) * n_repl}")
    print(f"{'═' * 75}\n")

    # 1. Очистка экспериментальной БД перед серией
    db = SessionLocal()
    print("[*] Очистка spc_state и spc_event перед стартом серии...")
    db.query(spc.SPCState).delete()
    db.query(spc.SPCEvent).delete()
    db.commit()
    print(f"    Очищено. Старт прогонов...\n")

    # 2. Подготовка CSV
    csv_path = RESULTS_DIR / f"{series_name}.csv"
    csv_columns = [
        "series", "scenario", "replication", "run_id", "source", "metric", "method",
        "true_change_step", "first_signal_step", "signal_count", "detection_delay",
        "is_false_alarm", "mu_hat", "sigma_hat", "baseline_size", "n_phase2_steps",
        "n_total_observations", "degradation", "deg_value", "deg_start", "seed",
    ]
    if csv_path.exists():
        csv_path.unlink()
    pd.DataFrame(columns=csv_columns).to_csv(csv_path, index=False)
    print(f"[*] Результаты будут писаться инкрементально в: {csv_path}\n")

    # 3. Прогон всех сценариев × всех репликаций
    total_runs = len(series["scenarios"]) * n_repl
    pbar = tqdm(total=total_runs, desc=f"Серия {series_key}", unit="run", ncols=90)

    start_time = time.time()
    for scenario_idx, scenario in enumerate(series["scenarios"]):
        # Локальный baseline для сценария (может быть переопределён, например в серии 4)
        baseline_size = scenario.get("baseline_size", base_baseline)

        for rep in range(1, n_repl + 1):
            seed = scenario_idx * 10000 + rep  # детерминированный, но разный для разных сценариев
            try:
                results = run_single_replication(
                    db=db,
                    series_name=series_name,
                    scenario=scenario,
                    replication=rep,
                    baseline_size=baseline_size,
                    seed=seed,
                )
                # Инкрементальная запись в CSV (3 строки на прогон — по одной на метод)
                pd.DataFrame(results).to_csv(csv_path, mode="a", header=False, index=False)
            except Exception as e:
                print(f"\n[!] Ошибка в {scenario['name']} rep {rep}: {e}")
                # продолжаем со следующего прогона
            finally:
                pbar.update(1)
                pbar.set_postfix_str(f"{scenario['name']} rep{rep:02d}")

    pbar.close()
    elapsed = time.time() - start_time
    print(f"\n[✓] Серия {series_key} завершена за {elapsed/60:.1f} минут")
    print(f"    Результаты: {csv_path}")

    db.close()
    return csv_path


# ─────────────────────────────────────────────────────────────────────────
# Главная точка входа
# ─────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Запуск экспериментальных серий SPC")
    parser.add_argument("--series", required=True,
                        help="Номер серии: '1', '2', '3', '4', '5' или 'all'")
    parser.add_argument("--replications", type=int, default=None,
                        help="Переопределить число повторений (по умолчанию из конфига)")
    parser.add_argument("--quick", action="store_true",
                        help="Быстрый прогон для проверки: 3 повторения вместо 30")
    args = parser.parse_args()

    # Инициализация экспериментальной БД (создаёт таблицы, если их нет)
    print("[*] Инициализация experiments_db...")
    try:
        init_experiments_db()
        print("    БД готова.\n")
    except Exception as e:
        print(f"\n[!] Не удалось подключиться к experiments_db: {e}")
        print("    Убедись, что:")
        print("      1. PostgreSQL запущен")
        print("      2. БД 'experiments_db' создана:")
        print("         psql -U postgres -c \"CREATE DATABASE experiments_db;\"")
        sys.exit(1)

    n_repl = 3 if args.quick else args.replications

    # Какие серии запускать
    if args.series == "all":
        series_keys = [k for k in ALL_SERIES.keys() if ALL_SERIES[k]["scenarios"]]
    elif args.series in ALL_SERIES:
        series_keys = [args.series]
    else:
        print(f"[!] Неизвестная серия: {args.series}")
        print(f"    Доступно: {list(ALL_SERIES.keys())} или 'all'")
        sys.exit(1)

    # Запуск
    for key in series_keys:
        run_series(key, replications_override=n_repl)

    print(f"\n{'═' * 75}")
    print(f"Все запланированные серии завершены.")
    print(f"CSV-файлы лежат в: {RESULTS_DIR}")
    print(f"{'═' * 75}")


if __name__ == "__main__":
    main()
