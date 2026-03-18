# таблица метрик
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from datetime import datetime
from server.database import Base

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    metric_name = Column(String)
    metric_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ExperimentConfig(Base):
    __tablename__ = "experiment_config"

    id         = Column(Integer, primary_key=True, index=True)
    config     = Column(JSON)  # всё в одном JSON-поле
    created_at = Column(DateTime, default=datetime.utcnow)