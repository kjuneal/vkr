import sqlite3

# создаём (или открываем) файл базы
conn = sqlite3.connect("source_b.db")

# создаём курсор
cursor = conn.cursor()

# создаём таблицу
cursor.execute("""
CREATE TABLE IF NOT EXISTS data (
    id INTEGER,
    timestamp TEXT,
    value REAL
)
""")

conn.commit()
conn.close()

print("База и таблица созданы!")