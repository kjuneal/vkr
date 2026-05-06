"""
Анализ результатов экспериментальных серий.

Использование:
    python -m experiments.analyze_experiments --series 1
    python -m experiments.analyze_experiments --series all

Скрипт читает CSV из experiments/results/ и выгружает:
  - Сводные таблицы (mean, std, 95% CI) в формате, удобном для вставки в ВКР.
  - Графики (matplotlib) в experiments/results/figures/.
  - Markdown-отчёт с интерпретацией для каждой серии.

Не зависит от БД. Работает только с CSV.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")  # без GUI
import matplotlib.pyplot as plt

RESULTS_DIR = Path(__file__).parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True)
REPORTS_DIR = RESULTS_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

METHOD_LABELS = {
    "shewhart": "Шухарт",
    "cusum":    "CUSUM",
    "ewma":     "EWMA",
}
METHOD_COLORS = {
    "shewhart": "#e74c3c",
    "cusum":    "#2ecc71",
    "ewma":     "#3498db",
}


# ─────────────────────────────────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────────────────────────────────
def confidence_interval_95(values: pd.Series) -> tuple[float, float]:
    """Возвращает 95% CI для среднего по выборке (нормальное приближение)."""
    values = values.dropna()
    if len(values) < 2:
        return (np.nan, np.nan)
    mean = values.mean()
    std  = values.std(ddof=1)
    margin = 1.96 * std / np.sqrt(len(values))
    return (mean - margin, mean + margin)


def summarize_method(group: pd.DataFrame) -> dict:
    """Сводная статистика по группе (одного метода в одном сценарии)."""
    delays = group["detection_delay"].dropna()
    n_total = len(group)
    n_signaled = group["first_signal_step"].notna().sum()
    n_false_alarms = group["is_false_alarm"].sum()

    if len(delays) > 0:
        mean_delay = delays.mean()
        std_delay  = delays.std(ddof=1) if len(delays) > 1 else 0.0
        ci_lo, ci_hi = confidence_interval_95(delays)
        median_delay = delays.median()
    else:
        mean_delay = std_delay = ci_lo = ci_hi = median_delay = np.nan

    return {
        "n_runs":           n_total,
        "n_signaled":       int(n_signaled),
        "n_false_alarms":   int(n_false_alarms),
        "detection_rate":   n_signaled / n_total if n_total else 0.0,
        "mean_delay":       mean_delay,
        "median_delay":     median_delay,
        "std_delay":        std_delay,
        "ci_95_low":        ci_lo,
        "ci_95_high":       ci_hi,
    }


def load_series_csv(series_name: str) -> pd.DataFrame | None:
    """Загрузить CSV серии. Возвращает None, если файла нет."""
    csv_path = RESULTS_DIR / f"{series_name}.csv"
    if not csv_path.exists():
        print(f"[!] CSV не найден: {csv_path}")
        return None
    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"[!] CSV пустой: {csv_path}")
        return None
    return df


# ─────────────────────────────────────────────────────────────────────────
# Анализ серии 1: ARL₀
# ─────────────────────────────────────────────────────────────────────────
def analyze_series_1(df: pd.DataFrame) -> str:
    """Серия 1 — валидация ARL₀. Все срабатывания = ложные тревоги."""
    summary_rows = []
    for method in ("shewhart", "cusum", "ewma"):
        sub = df[df["method"] == method]
        # ARL₀ = средняя задержка до первого ложного срабатывания
        # Прогоны без срабатывания подавляются (дают цензурированную оценку)
        s = summarize_method(sub)
        s["method"] = METHOD_LABELS[method]
        s["theoretical_arl0"] = {"shewhart": 370, "cusum": 465, "ewma": 370}[method]
        summary_rows.append(s)

    summary = pd.DataFrame(summary_rows)
    summary = summary[["method", "n_runs", "n_signaled", "mean_delay",
                       "median_delay", "ci_95_low", "ci_95_high",
                       "theoretical_arl0"]]
    summary = summary.rename(columns={
        "method":            "Метод",
        "n_runs":            "Прогонов",
        "n_signaled":        "Сработало",
        "mean_delay":        "Эмп. ARL₀",
        "median_delay":      "Медиана",
        "ci_95_low":         "CI 95% низ",
        "ci_95_high":        "CI 95% верх",
        "theoretical_arl0":  "Теор. ARL₀",
    })

    out_path = REPORTS_DIR / "series1_arl0_summary.csv"
    summary.to_csv(out_path, index=False, float_format="%.1f")

    # График: распределение времён до первого срабатывания
    fig, ax = plt.subplots(figsize=(10, 5))
    for method in ("shewhart", "cusum", "ewma"):
        sub = df[df["method"] == method]
        delays = sub["detection_delay"].dropna()
        ax.hist(delays, bins=20, alpha=0.5,
                label=METHOD_LABELS[method], color=METHOD_COLORS[method])

    ax.set_xlabel("Шаг первого ложного срабатывания (окна)")
    ax.set_ylabel("Число прогонов")
    ax.set_title("Серия 1: распределение времён до ложного срабатывания (ARL₀)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "series1_arl0_histogram.png", dpi=130)
    plt.close(fig)

    return _format_report("Серия 1: Валидация ARL₀", summary, [
        ("series1_arl0_summary.csv",     "Сводная таблица"),
        ("figures/series1_arl0_histogram.png", "Гистограмма распределения времён"),
    ])


# ─────────────────────────────────────────────────────────────────────────
# Анализ серии 2: ARL₁ vs величина сдвига
# ─────────────────────────────────────────────────────────────────────────
def analyze_series_2(df: pd.DataFrame) -> str:
    # Извлекаем величину сдвига из имени сценария: shift_0.5sigma → 0.5
    df = df.copy()
    df["shift_sigma"] = df["scenario"].str.extract(r"shift_([\d.]+)sigma").astype(float)

    summary_rows = []
    for shift in sorted(df["shift_sigma"].unique()):
        for method in ("shewhart", "cusum", "ewma"):
            sub = df[(df["shift_sigma"] == shift) & (df["method"] == method)]
            s = summarize_method(sub)
            s["shift_sigma"] = shift
            s["method"] = METHOD_LABELS[method]
            summary_rows.append(s)

    summary = pd.DataFrame(summary_rows)
    pivot = summary.pivot_table(
        index="shift_sigma",
        columns="method",
        values="mean_delay",
    ).round(1)

    out_path = REPORTS_DIR / "series2_arl1_table.csv"
    pivot.to_csv(out_path, float_format="%.1f")

    # График: задержка обнаружения от величины сдвига
    fig, ax = plt.subplots(figsize=(10, 6))
    for method in ("shewhart", "cusum", "ewma"):
        method_label = METHOD_LABELS[method]
        sub = summary[summary["method"] == method_label].sort_values("shift_sigma")
        ax.errorbar(
            sub["shift_sigma"], sub["mean_delay"],
            yerr=[sub["mean_delay"] - sub["ci_95_low"],
                  sub["ci_95_high"] - sub["mean_delay"]],
            label=method_label, color=METHOD_COLORS[method],
            marker="o", linewidth=2, capsize=4,
        )

    ax.set_xlabel("Величина сдвига (в единицах σ окна)")
    ax.set_ylabel("Средняя задержка обнаружения (окна)")
    ax.set_title("Серия 2: Чувствительность методов к величине сдвига (ARL₁)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "series2_arl1_curve.png", dpi=130)
    plt.close(fig)

    return _format_report("Серия 2: Чувствительность к величине сдвига", pivot.reset_index(), [
        ("series2_arl1_table.csv",        "Таблица ARL₁ по сдвигам и методам"),
        ("figures/series2_arl1_curve.png", "График зависимости задержки от сдвига"),
    ])


# ─────────────────────────────────────────────────────────────────────────
# Анализ серии 3: сравнение методов на типах деградации
# ─────────────────────────────────────────────────────────────────────────
def analyze_series_3(df: pd.DataFrame) -> str:
    summary_rows = []
    for scenario in df["scenario"].unique():
        for method in ("shewhart", "cusum", "ewma"):
            sub = df[(df["scenario"] == scenario) & (df["method"] == method)]
            s = summarize_method(sub)
            s["scenario"] = scenario
            s["method"]   = METHOD_LABELS[method]
            summary_rows.append(s)

    summary = pd.DataFrame(summary_rows)
    pivot_delay = summary.pivot_table(
        index="scenario",
        columns="method",
        values="mean_delay",
    ).round(1)
    pivot_rate = summary.pivot_table(
        index="scenario",
        columns="method",
        values="detection_rate",
    ).round(2)

    out_delay = REPORTS_DIR / "series3_comparison_delay.csv"
    out_rate  = REPORTS_DIR / "series3_comparison_rate.csv"
    pivot_delay.to_csv(out_delay, float_format="%.1f")
    pivot_rate.to_csv(out_rate, float_format="%.2f")

    # Барчарт: средняя задержка обнаружения по сценариям
    scenarios = list(pivot_delay.index)
    methods   = ["Шухарт", "CUSUM", "EWMA"]
    x = np.arange(len(scenarios))
    width = 0.25

    fig, ax = plt.subplots(figsize=(11, 6))
    for i, method in enumerate(methods):
        if method in pivot_delay.columns:
            values = pivot_delay[method].values
            method_key = {"Шухарт": "shewhart", "CUSUM": "cusum", "EWMA": "ewma"}[method]
            ax.bar(x + i*width, values, width, label=method,
                   color=METHOD_COLORS[method_key])

    ax.set_xlabel("Тип деградации")
    ax.set_ylabel("Средняя задержка обнаружения (окна)")
    ax.set_title("Серия 3: Сравнение методов на разных типах деградации")
    ax.set_xticks(x + width)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "series3_comparison_bars.png", dpi=130)
    plt.close(fig)

    return _format_report("Серия 3: Сравнение методов", pivot_delay.reset_index(), [
        ("series3_comparison_delay.csv",       "Средние задержки"),
        ("series3_comparison_rate.csv",        "Доля прогонов с обнаружением"),
        ("figures/series3_comparison_bars.png", "Сравнительный барчарт"),
    ])


# ─────────────────────────────────────────────────────────────────────────
# Анализ серии 4: границы применимости
# ─────────────────────────────────────────────────────────────────────────
def analyze_series_4(df: pd.DataFrame) -> str:
    df = df.copy()

    # Сценарии 4а: baseline_<bs>
    df_bs = df[df["scenario"].str.startswith("baseline_")].copy()
    if not df_bs.empty:
        df_bs["bs_value"] = df_bs["scenario"].str.extract(r"baseline_(\d+)").astype(int)

    # Сценарии 4б: spikes_<p>pct
    df_sp = df[df["scenario"].str.startswith("spikes_")].copy()
    if not df_sp.empty:
        df_sp["spike_pct"] = df_sp["scenario"].str.extract(r"spikes_(\d+)pct").astype(int)

    # 4а: ARL₀ в зависимости от длины baseline
    if not df_bs.empty:
        rows_a = []
        for bs in sorted(df_bs["bs_value"].unique()):
            for method in ("shewhart", "cusum", "ewma"):
                sub = df_bs[(df_bs["bs_value"] == bs) & (df_bs["method"] == method)]
                s = summarize_method(sub)
                s["baseline_size"] = bs
                s["method"] = METHOD_LABELS[method]
                rows_a.append(s)
        sub_a = pd.DataFrame(rows_a)
        pivot_a = sub_a.pivot_table(
            index="baseline_size",
            columns="method",
            values="mean_delay",
        ).round(1)
        pivot_a.to_csv(REPORTS_DIR / "series4a_baseline_arl0.csv", float_format="%.1f")

        # График
        fig, ax = plt.subplots(figsize=(10, 6))
        for method in ("shewhart", "cusum", "ewma"):
            method_label = METHOD_LABELS[method]
            if method_label in pivot_a.columns:
                ax.plot(pivot_a.index, pivot_a[method_label], marker="o",
                        label=method_label, color=METHOD_COLORS[method], linewidth=2)
        ax.set_xlabel("Длина фазы I (baseline_size)")
        ax.set_ylabel("Эмпирическое ARL₀")
        ax.set_title("Серия 4а: Влияние длины baseline на ARL₀")
        ax.axhline(y=370, linestyle="--", color="grey", alpha=0.5,
                   label="теор. ARL₀ ≈ 370")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "series4a_baseline_arl0.png", dpi=130)
        plt.close(fig)

    # 4б: чувствительность к доле выбросов
    if not df_sp.empty:
        rows_b = []
        for sp in sorted(df_sp["spike_pct"].unique()):
            for method in ("shewhart", "cusum", "ewma"):
                sub = df_sp[(df_sp["spike_pct"] == sp) & (df_sp["method"] == method)]
                s = summarize_method(sub)
                s["spike_pct"] = sp
                s["method"] = METHOD_LABELS[method]
                rows_b.append(s)
        sub_b = pd.DataFrame(rows_b)
        pivot_b = sub_b.pivot_table(
            index="spike_pct",
            columns="method",
            values="mean_delay",
        ).round(1)
        pivot_b.to_csv(REPORTS_DIR / "series4b_spikes.csv", float_format="%.1f")

        fig, ax = plt.subplots(figsize=(10, 6))
        for method in ("shewhart", "cusum", "ewma"):
            method_label = METHOD_LABELS[method]
            if method_label in pivot_b.columns:
                ax.plot(pivot_b.index, pivot_b[method_label], marker="s",
                        label=method_label, color=METHOD_COLORS[method], linewidth=2)
        ax.set_xlabel("Доля выбросов (%)")
        ax.set_ylabel("Средняя задержка обнаружения (окна)")
        ax.set_title("Серия 4б: Влияние доли выбросов на чувствительность")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "series4b_spikes.png", dpi=130)
        plt.close(fig)

    return _format_report("Серия 4: Границы применимости", None, [
        ("series4a_baseline_arl0.csv",         "Зависимость ARL₀ от baseline"),
        ("series4b_spikes.csv",                "Зависимость задержки от выбросов"),
        ("figures/series4a_baseline_arl0.png", "График: baseline → ARL₀"),
        ("figures/series4b_spikes.png",        "График: выбросы → задержка"),
    ])


# ─────────────────────────────────────────────────────────────────────────
# Форматирование отчёта
# ─────────────────────────────────────────────────────────────────────────
def _format_report(title: str, summary_df, files: list[tuple[str, str]]) -> str:
    out = [f"# {title}\n"]
    if summary_df is not None and not summary_df.empty:
        out.append("## Сводная таблица\n")
        out.append("```")
        out.append(summary_df.to_string(index=False))
        out.append("```\n")
    out.append("## Сгенерированные файлы\n")
    for path, desc in files:
        out.append(f"- `{path}` — {desc}")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────
# Главная точка входа
# ─────────────────────────────────────────────────────────────────────────
SERIES_ANALYZERS = {
    "1": ("series1_arl0",       analyze_series_1),
    "2": ("series2_arl1",       analyze_series_2),
    "3": ("series3_comparison", analyze_series_3),
    "4": ("series4_boundaries", analyze_series_4),
}


def main():
    parser = argparse.ArgumentParser(description="Анализ результатов экспериментов")
    parser.add_argument("--series", required=True,
                        help="Номер серии: '1', '2', '3', '4' или 'all'")
    args = parser.parse_args()

    if args.series == "all":
        keys = list(SERIES_ANALYZERS.keys())
    elif args.series in SERIES_ANALYZERS:
        keys = [args.series]
    else:
        print(f"[!] Неизвестная серия: {args.series}")
        sys.exit(1)

    for key in keys:
        series_name, analyzer = SERIES_ANALYZERS[key]
        print(f"\n{'═' * 60}")
        print(f"СЕРИЯ {key}: {series_name}")
        print(f"{'═' * 60}")

        df = load_series_csv(series_name)
        if df is None:
            continue

        report = analyzer(df)
        report_path = REPORTS_DIR / f"{series_name}_report.md"
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"\n[✓] Отчёт сохранён: {report_path}")


if __name__ == "__main__":
    main()
