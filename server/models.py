# таблица метрик
from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from server.database import Base

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    metric_name = Column(String)
    metric_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)