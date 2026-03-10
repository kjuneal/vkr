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



# import pandas as pd
# from sqlalchemy import create_engine
# from urllib.parse import quote_plus

# # параметры подключения
# user = quote_plus("postgres")
# password = quote_plus("12345")
# host = "localhost"
# port = "5432"
# database = quote_plus("source_a")

# # создаём движок с явной кодировкой UTF-8
# engine = create_engine(
#     f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
#     connect_args={"client_encoding": "utf8"}
# )

# # проверка подключения
# try:
#     with engine.connect() as conn:
#         print("Connected!")
# except Exception as e:
#     print("Ошибка подключения:", e)


# import psycopg

# try:
#     with psycopg.connect(
#         "dbname=source_a.db user=postgres password=12345 host=localhost port=5432"
#     ) as conn:
#         print("Connected!")
# except Exception as e:
#     print("Ошибка подключения:", e)