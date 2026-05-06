import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean,  Index
from datetime import datetime
from typing import Optional

from server.database import Base

# добавлена колонка run_id для разделения
# параллельных экспериментов. Для UI-режима (один эксперимент за раз) run_id
# остаётся NULL и поведение полностью совпадает с прежним.
class SPCState(Base):
    __tablename__ = "spc_state"

    id            = Column(Integer, primary_key=True, index=True)
    run_id        = Column(String, index=True, nullable=True) 
    source        = Column(String, index=True) # источник
    metric_name   = Column(String, index=True) # метрика

    n_baseline    = Column(Integer, default=0) # записей в окне
    mu_hat        = Column(Float,   default=None) # мат ожидание генерируемой выборки
    sigma_hat     = Column(Float,   default=None) # стд отклонение генерируемой выборки
    m2            = Column(Float,   default=0.0) # для алгоритма Уэлфорда

    ucl           = Column(Float, default=None) # верхняя граница
    lcl           = Column(Float, default=None) # нижняя граница

    cusum_pos     = Column(Float, default=0.0) # поз КУСУМ
    cusum_neg     = Column(Float, default=0.0) # нег КУСУМ
 
    ewma_z        = Column(Float, default=None) # взвешенное скользящее среднее
    ewma_step     = Column(Integer, default=0) 

    status          = Column(String,  default="collecting") #
    signal_shewhart = Column(Boolean, default=False) #
    signal_cusum    = Column(Boolean, default=False) #
    signal_ewma     = Column(Boolean, default=False) #
    last_signal_at  = Column(DateTime, default=None) #
    updated_at      = Column(DateTime, default=datetime.utcnow) #

    __table_args__ = (
        Index("ix_spc_state_run_source_metric", "run_id", "source", "metric_name"),
    )


# ────────────────────────────────────────────────────────────────────────────
# Лог отдельных событий — каждое срабатывание любого из методов.
#
# Используется для расчёта момента ПЕРВОГО срабатывания, статистики ARL₀/ARL₁
# и полной реконструкции хода эксперимента.

class SPCEvent(Base):
    __tablename__ = "spc_event"

    id            = Column(Integer, primary_key=True, index=True)
    run_id        = Column(String, index=True, nullable=True)
    source        = Column(String, index=True)
    metric_name   = Column(String, index=True)
    method        = Column(String, index=True)  # "shewhart" | "cusum" | "ewma"
    step          = Column(Integer)              # номер окна в фазе II (1, 2, 3, ...)
    value         = Column(Float)                # значение метрики, на котором сработало
    mu_hat        = Column(Float)                # mu_hat на момент срабатывания
    sigma_hat     = Column(Float)
    cusum_pos     = Column(Float, default=None)  # для метода cusum
    cusum_neg     = Column(Float, default=None)
    ewma_z        = Column(Float, default=None)  # для метода ewma
    created_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_spc_event_run_method", "run_id", "method"),
        Index("ix_spc_event_run_source_metric_method", "run_id", "source", "metric_name", "method"),
    )


# Дефолтные параметры (используются в UI-режиме)
DEFAULT_BASELINE_SIZE = 50  # Изменено с 10 на 50 для корректной фазы I
CUSUM_K       = 0.5
CUSUM_H       = 5.0
EWMA_LAMBDA   = 0.2
EWMA_L        = 3.0
SPC_METRICS   = {"mean", "std", "completeness", "median", "iqr"}





def update_spc(
    db: Session,
    source: str,
    metric_name: str,
    new_value: float,
    run_id: Optional[str] = None,
    baseline_size: int = DEFAULT_BASELINE_SIZE,
) -> SPCState:
    """
    Обработать новое значение метрики через карту Шухарта + CUSUM + EWMA.

    Аргументы:
        db          — SQLAlchemy session
        source      — идентификатор источника (например, "source_a")
        metric_name — имя метрики ("mean", "std", "completeness", ...)
        new_value   — новое значение метрики
        run_id      — идентификатор прогона эксперимента; для UI оставлять None
        baseline_size — длина фазы I; для UI используется 50, эксперименты могут передавать своё значение

    Возвращает обновлённое SPCState.
    """

    if new_value is None or (isinstance(new_value, float) and np.isnan(new_value)):
        return _get_or_create_state(db, run_id, source, metric_name)

    state = _get_or_create_state(db, run_id, source, metric_name)

    # ── Фаза I: накопление baseline ────────────────────────────────────────────────────────────
    if state.n_baseline < baseline_size:
        state.n_baseline += 1

        if state.n_baseline == 1:
            state.mu_hat    = new_value
            state.sigma_hat = 0.0
            state.m2        = 0.0
        else: # Вычисление дисперсии по алгоритму Уэлфорда (одиночный проход)
            delta           = new_value - state.mu_hat
            state.mu_hat    = float(state.mu_hat + delta / state.n_baseline)
            delta2          = new_value - state.mu_hat
            state.m2        = float(state.m2 + delta * delta2)
            state.sigma_hat = float(np.sqrt(state.m2 / (state.n_baseline - 1)))

        state.status     = "collecting"
        state.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(state)
        return state

    # ── Фаза II: контроль ───────────────────────────────────────────────────────────
    if state.ucl is None: # Вычисление границ для Шухарта, правило 3 сигм 99,7
        # Первый шаг фазы II — инициализируем границы и EWMA
        state.ucl    = state.mu_hat + 3 * state.sigma_hat
        state.lcl    = state.mu_hat - 3 * state.sigma_hat
        state.ewma_z = state.mu_hat
    
    # Инкрементируем номер шага в фазе II (для EWMA-границы)
    state.ewma_step = (state.ewma_step or 0) + 1
    step = state.ewma_step

    sigma = state.sigma_hat if state.sigma_hat and state.sigma_hat > 0 else 1e-9

     # ── Карта Шухарта ────────────────────────────────────────────────────
    signal_shewhart = (new_value > state.ucl) or (new_value < state.lcl) # Проверка выхода за границы 

    # ── CUSUM ─────────────────────────────────────────────────────────────
    k = CUSUM_K * sigma
    h = CUSUM_H * sigma # Граница КУСУМа
    state.cusum_pos = max(0.0, state.cusum_pos + (new_value - state.mu_hat) - k)
    state.cusum_neg = max(0.0, state.cusum_neg - (new_value - state.mu_hat) - k)
    signal_cusum = (state.cusum_pos > h) or (state.cusum_neg > h)
    if signal_cusum:
        state.cusum_pos = h / 2
        state.cusum_neg = h / 2

    # ── EWMA ──────────────────────────────────────────────────────────────
    state.ewma_z   = EWMA_LAMBDA * new_value + (1 - EWMA_LAMBDA) * state.ewma_z

    # Точная формула стд. отклонения EWMA с поправкой для начальных шагов:
    #   σ_z(t) = σ · √( λ/(2-λ) · (1 - (1-λ)^(2t)) )
    # При больших t стремится к асимптотической σ · √(λ/(2-λ)).
    asymptotic_factor = EWMA_LAMBDA / (2 - EWMA_LAMBDA)
    transient_factor  = 1 - (1 - EWMA_LAMBDA) ** (2 * step)
    ewma_sigma        = sigma * np.sqrt(asymptotic_factor * transient_factor)

    signal_ewma    = (
        state.ewma_z > state.mu_hat + EWMA_L * ewma_sigma or state.ewma_z < state.mu_hat - EWMA_L * ewma_sigma
    )

    # ── Запись срабатываний в SPCEvent ───────────────────────────────────
    if signal_shewhart:
        _log_event(db, run_id, source, metric_name, "shewhart", step, new_value, state)
    if signal_cusum:
        _log_event(db, run_id, source, metric_name, "cusum", step, new_value, state)
    if signal_ewma:
        _log_event(db, run_id, source, metric_name, "ewma", step, new_value, state)

    
    # Обновление состояния
    state.signal_shewhart = signal_shewhart
    state.signal_cusum    = signal_cusum
    state.signal_ewma     = signal_ewma

    if signal_shewhart:
        state.status = "critical"
    elif signal_cusum or signal_ewma:
        state.status = "warning"
    else:
        state.status = "normal"

    if signal_shewhart or signal_cusum or signal_ewma:
        state.last_signal_at = datetime.utcnow()

    state.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(state)
    return state

def _log_event(
    db: Session,
    run_id: Optional[str],
    source: str,
    metric_name: str,
    method: str,
    step: int,
    value: float,
    state: SPCState,
) -> None:
    """Записать одно срабатывание в SPCEvent."""
    event = SPCEvent(
        run_id=run_id,
        source=source,
        metric_name=metric_name,
        method=method,
        step=step,
        value=value,
        mu_hat=state.mu_hat,
        sigma_hat=state.sigma_hat,
        cusum_pos=state.cusum_pos if method == "cusum" else None,
        cusum_neg=state.cusum_neg if method == "cusum" else None,
        ewma_z=state.ewma_z if method == "ewma" else None,
    )
    db.add(event)
    # commit будет вызван в update_spc()

def _get_or_create_state(db: Session, run_id: Optional[str], source: str, metric_name: str) -> SPCState:
    """Найти или создать SPCState для конкретного (run_id, source, metric_name)."""
    state = (
        db.query(SPCState)
        .filter(
            SPCState.run_id == run_id,
            SPCState.source == source,
            SPCState.metric_name == metric_name,
        )
        .first()
    )
    if state is None:
        state = SPCState(run_id=run_id, source=source, metric_name=metric_name)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_all_states(db: Session, run_id: Optional[str] = None) -> list[SPCState]:
    q = db.query(SPCState)
    if run_id is not None:
        q = q.filter(SPCState.run_id == run_id)
    else:
        q = q.filter(SPCState.run_id.is_(None))
    return q.all()


def get_state(db: Session, source: str, metric_name: str, run_id: Optional[str] = None) -> SPCState | None:
    q = db.query(SPCState).filter(
        SPCState.source == source,
        SPCState.metric_name == metric_name,
    )
    if run_id is not None:
        q = q.filter(SPCState.run_id == run_id)
    else:
        q = q.filter(SPCState.run_id.is_(None))
    return q.first()


def get_events(
    db: Session,
    run_id: Optional[str] = None,
    source: Optional[str] = None,
    metric_name: Optional[str] = None,
    method: Optional[str] = None,
) -> list[SPCEvent]:
    """Получить лог событий по фильтру."""
    q = db.query(SPCEvent)
    if run_id is not None:
        q = q.filter(SPCEvent.run_id == run_id)
    if source is not None:
        q = q.filter(SPCEvent.source == source)
    if metric_name is not None:
        q = q.filter(SPCEvent.metric_name == metric_name)
    if method is not None:
        q = q.filter(SPCEvent.method == method)
    return q.order_by(SPCEvent.step).all()


def get_first_event(
    db: Session,
    run_id: str,
    source: str,
    metric_name: str,
    method: str,
) -> SPCEvent | None:
    """Получить ПЕРВОЕ срабатывание данного метода в данном прогоне."""
    return (
        db.query(SPCEvent)
        .filter(
            SPCEvent.run_id == run_id,
            SPCEvent.source == source,
            SPCEvent.metric_name == metric_name,
            SPCEvent.method == method,
        )
        .order_by(SPCEvent.step.asc())
        .first()
    )