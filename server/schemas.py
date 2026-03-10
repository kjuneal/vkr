# модель API
from pydantic import BaseModel
from datetime import datetime
from typing import Dict


# что отправляют агенты
class MetricsBatch(BaseModel):
    source: str
    timestamp: datetime
    metrics: Dict[str, float]


# одна строка таблицы (как хранится в БД)
class MetricCreate(BaseModel):
    source: str
    metric_name: str
    metric_value: float
    timestamp: datetime