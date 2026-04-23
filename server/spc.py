import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from datetime import datetime

from server.database import Base


class SPCState(Base):
    __tablename__ = "spc_state"

    id            = Column(Integer, primary_key=True, index=True)
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

    status          = Column(String,  default="collecting") #
    signal_shewhart = Column(Boolean, default=False) #
    signal_cusum    = Column(Boolean, default=False) #
    signal_ewma     = Column(Boolean, default=False) #
    last_signal_at  = Column(DateTime, default=None) #
    updated_at      = Column(DateTime, default=datetime.utcnow) #


BASELINE_SIZE = 10 #############   5, 10
CUSUM_K       = 0.5
CUSUM_H       = 5.0
EWMA_LAMBDA   = 0.2
EWMA_L        = 3.0
SPC_METRICS   = {"mean", "std", "completeness", "median", "iqr"}


def update_spc(db: Session, source: str, metric_name: str, new_value: float) -> SPCState:

    if new_value is None or (isinstance(new_value, float) and np.isnan(new_value)):
        return _get_or_create_state(db, source, metric_name)

    state = _get_or_create_state(db, source, metric_name)

    # ── Фаза I ────────────────────────────────────────────────────────────
    if state.n_baseline < BASELINE_SIZE:
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

    # ── Фаза II ───────────────────────────────────────────────────────────
    if state.ucl is None: # Вычисление границ для Шухарта, правило 3 сигм 99,7
        state.ucl    = state.mu_hat + 3 * state.sigma_hat
        state.lcl    = state.mu_hat - 3 * state.sigma_hat
        state.ewma_z = state.mu_hat

    sigma = state.sigma_hat if state.sigma_hat and state.sigma_hat > 0 else 1e-9

    # Шухарт
    signal_shewhart = (new_value > state.ucl) or (new_value < state.lcl) # Проверка выхода за границы 

    # CUSUM
    k = CUSUM_K * sigma
    h = CUSUM_H * sigma # Граница КУСУМа
    state.cusum_pos = max(0.0, state.cusum_pos + (new_value - state.mu_hat) - k)
    state.cusum_neg = max(0.0, state.cusum_neg - (new_value - state.mu_hat) - k)
    signal_cusum = (state.cusum_pos > h) or (state.cusum_neg > h)
    if signal_cusum:
        state.cusum_pos = h / 2
        state.cusum_neg = h / 2

    # EWMA
    state.ewma_z   = EWMA_LAMBDA * new_value + (1 - EWMA_LAMBDA) * state.ewma_z
    ewma_sigma     = sigma * np.sqrt(EWMA_LAMBDA / (2 - EWMA_LAMBDA))
    signal_ewma    = (
        state.ewma_z > state.mu_hat + EWMA_L * ewma_sigma or state.ewma_z < state.mu_hat - EWMA_L * ewma_sigma
    )

    # Статус
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


def _get_or_create_state(db: Session, source: str, metric_name: str) -> SPCState:
    state = (
        db.query(SPCState)
        .filter(SPCState.source == source, SPCState.metric_name == metric_name)
        .first()
    )
    if state is None:
        state = SPCState(source=source, metric_name=metric_name)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_all_states(db: Session) -> list[SPCState]:
    return db.query(SPCState).all()


def get_state(db: Session, source: str, metric_name: str) -> SPCState | None:
    return (
        db.query(SPCState)
        .filter(SPCState.source == source, SPCState.metric_name == metric_name)
        .first()
    )