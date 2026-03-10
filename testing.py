# import pandas as pd

# df = pd.read_csv("source_a.csv")
# print(df.head())

# import sqlite3
# import pandas as pd

# conn = sqlite3.connect("source_b.db")

# df = pd.read_sql("SELECT * FROM data LIMIT 10", conn)

# print(df)

# conn.close()

# import sqlite3
# import pandas as pd

# conn = sqlite3.connect("source_b.db")

# count = pd.read_sql("SELECT COUNT(*) as c FROM data", conn)
# print(count)

# conn.close()

import sqlite3
import pandas as pd

conn = sqlite3.connect("source_b.db")

df = pd.read_sql("SELECT * FROM data LIMIT 50", conn)

completeness = 1 - df["value"].isna().sum() / len(df)
mean_value = df["value"].mean()

print("Completeness:", completeness)
print("Mean:", mean_value)

conn.close()