import pandas as pd
import sqlite3

# читаем CSV
df = pd.read_csv("data/source_b.csv")

# подключаемся к базе
conn = sqlite3.connect("source_b.db")

# записываем в таблицу
df.to_sql("data", conn, if_exists="replace", index=False)

conn.close()

print("Данные загружены!")