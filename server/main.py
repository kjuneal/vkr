# # venv\Scripts\activate
# # uvicorn server.main:app --reload
# # server\main.py


# DROP TABLE IF EXISTS spc_state;
# DROP TABLE IF EXISTS metrics;
# -- TRUNCATE TABLE metrics RESTART IDENTITY;

# from fastapi import FastAPI, Depends
# from sqlalchemy.orm import Session

# from server import models
# from server import schemas
# from server import crud
# from server.database import engine, SessionLocal

# models.Base.metadata.create_all(bind=engine)

# app = FastAPI()

# @app.get("/")
# def root():
#     return {"status": "ok"}

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # проверка
# # @app.post("/metrics")
# # def receive_metrics(data: dict):
# #     print(data)
# #     return {"status": "ok"}

# @app.post("/metrics/")
# def receive_metrics(batch: schemas.MetricsBatch, db: Session = Depends(get_db)):

#     results = []

#     for name, value in batch.metrics.items():
#         metric = schemas.MetricCreate(
#             source=batch.source,
#             metric_name=name,
#             metric_value=value,
#             timestamp=batch.timestamp
#         )

#         result = crud.create_metric(db=db, metric=metric)
#         results.append(result)

#     return results

# server/main.py — обновлённая версия

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from server import models, schemas, crud
from server import spc
from server.database import engine, SessionLocal
from server.models import Metric

# Создаём таблицы (включая новую spc_state)
models.Base.metadata.create_all(bind=engine)
spc.SPCState.metadata.create_all(bind=engine)  # ← добавить

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/metrics/")
def receive_metrics(batch: schemas.MetricsBatch, db: Session = Depends(get_db)):
    results = []

    for name, value in batch.metrics.items():
        # 1. Сохраняем метрику как раньше
        metric = schemas.MetricCreate(
            source=batch.source,
            metric_name=name,
            metric_value=value,
            timestamp=batch.timestamp
        )
        crud.create_metric(db=db, metric=metric)

        ## 2. Запускаем SPC-анализ ← новое
        ## spc.update_spc(db=db, source=batch.source, metric_name=name, new_value=value)
        # SPC только для нужных метрик
        if name in spc.SPC_METRICS:
            spc.update_spc(db=db, source=batch.source, metric_name=name, new_value=value)

        results.append({"source": batch.source, "metric": name, "value": value})

    return results


# ── Эндпоинты для Streamlit ───────────────────────────────────────────────
@app.get("/spc/")
def get_all_spc_states(db: Session = Depends(get_db)):
    states = spc.get_all_states(db)
    return [_state_to_dict(s, db) for s in states]

@app.get("/spc/{source}/{metric_name}")
def get_spc_state(source: str, metric_name: str, db: Session = Depends(get_db)):
    state = spc.get_state(db, source, metric_name)
    if state is None:
        return {"error": "not found"}
    return _state_to_dict(state, db)

def _state_to_dict(s, db: Session = None) -> dict:
    # Получаем последнее значение метрики из таблицы metrics
    last_value = None
    if db:
        last = (
            db.query(Metric)
            .filter(Metric.source == s.source, Metric.metric_name == s.metric_name)
            .order_by(Metric.timestamp.desc())
            .first()
        )
        if last:
            last_value = last.metric_value

    return {
        "source":           s.source,
        "metric_name":      s.metric_name,
        "status":           s.status,
        "n_baseline":       s.n_baseline,
        "mu_hat":           s.mu_hat,
        "sigma_hat":        s.sigma_hat,
        "ucl":              s.ucl,
        "lcl":              s.lcl,
        "cusum_pos":        s.cusum_pos,
        "cusum_neg":        s.cusum_neg,
        "ewma_z":           s.ewma_z,
        "last_value":       last_value,   # ← новое поле
        "signal_shewhart":  s.signal_shewhart,
        "signal_cusum":     s.signal_cusum,
        "signal_ewma":      s.signal_ewma,
        "last_signal_at":   str(s.last_signal_at) if s.last_signal_at else None,
        "updated_at":       str(s.updated_at),
    }



@app.get("/metrics/history/{source}/{metric_name}")
def get_metrics_history(source: str, metric_name: str, limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(Metric)
        .filter(Metric.source == source, Metric.metric_name == metric_name)
        .order_by(Metric.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [{"timestamp": str(r.timestamp), "value": r.metric_value} for r in rows]

@app.delete("/reset/")
def reset_experiment(db: Session = Depends(get_db)):
    db.query(models.Metric).delete()
    db.query(spc.SPCState).delete()
    db.commit()
    return {"status": "cleared"}