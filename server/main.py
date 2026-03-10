# venv\Scripts\activate
# uvicorn server.main:app --reload
# server\main.py

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from server import models
from server import schemas
from server import crud
from server.database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# проверка
# @app.post("/metrics")
# def receive_metrics(data: dict):
#     print(data)
#     return {"status": "ok"}

@app.post("/metrics/")
def receive_metrics(batch: schemas.MetricsBatch, db: Session = Depends(get_db)):

    results = []

    for name, value in batch.metrics.items():
        metric = schemas.MetricCreate(
            source=batch.source,
            metric_name=name,
            metric_value=value,
            timestamp=batch.timestamp
        )

        result = crud.create_metric(db=db, metric=metric)
        results.append(result)

    return results