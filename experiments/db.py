"""
Подключение к экспериментальной БД (отдельной от UI).

Перед первым запуском нужно создать БД вручную в PostgreSQL:
    CREATE DATABASE experiments_db;

Затем при первом импорте этого модуля в neё автоматически создадутся
таблицы spc_state и spc_event через Base.metadata.create_all().
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Импорт Base и моделей из основного проекта.
# Это критически важно — мы переиспользуем те же ORM-классы SPCState/SPCEvent.
from server.database import Base
from server import spc  # импорт нужен, чтобы зарегистрировать SPCState и SPCEvent в Base


EXPERIMENTS_DATABASE_URL = "postgresql://postgres:12345@localhost:5432/experiments"

engine = create_engine(EXPERIMENTS_DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_experiments_db() -> None:
    """Создать таблицы spc_state и spc_event в экспериментальной БД, если их ещё нет."""
    Base.metadata.create_all(bind=engine)
