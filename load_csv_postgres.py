import pandas as pd
from sqlalchemy import create_engine

# параметры подключения
user = "postgres"
password = "12345"
host = "localhost"
port = "5432"
database = "source_a.db"

# создаём движок SQLAlchemy
engine = create_engine(
    f"postgresql://{user}:{password}@{host}:{port}/{database}"
)

# проверяем соединение
with engine.connect() as conn:
    print("Connected to PostgreSQL!")

# читаем CSV (относительный путь к папке data)
df = pd.read_csv("data/source_a.csv")  

# загружаем в таблицу PostgreSQL
df.to_sql("data", engine, if_exists="replace", index=False)

print("Данные загружены в PostgreSQL")
