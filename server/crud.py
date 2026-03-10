# работа с БД
from sqlalchemy.orm import Session
from server import models
from server import schemas


def create_metric(db: Session, metric: schemas.MetricCreate):

    db_metric = models.Metric(
        source=metric.source,
        metric_name=metric.metric_name,
        metric_value=metric.metric_value,
        timestamp=metric.timestamp
    )

    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)

    return db_metric