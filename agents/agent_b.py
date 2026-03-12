# agent b // python -m agents.agent_b
import pandas as pd
import sqlite3
from agents.base_agent import BaseAgent


# class AgentB(BaseAgent):

#     def __init__(self, db_path, server_url):
#         super().__init__(server_url)
#         self.db_path = db_path

#     def compute_metrics(self):
#         conn = sqlite3.connect(self.db_path)
#         # df = pd.read_sql("SELECT * FROM data", conn)
#         df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", conn)
#         conn.close()

#         total = len(df)
#         missing = df["value"].isna().sum()

#         return {
#             "completeness": float(1 - missing / total),
#             "missing_count": int(missing),
#             "count": total
#         }

#     def run(self):
#         metrics = self.compute_metrics()
#         return self.send_metrics("source_b", metrics)


# if __name__ == "__main__":
#     agent = AgentB("source_b.db", "http://127.0.0.1:8000")
#     print(agent.run())

# agent_b_stream.py

import time

class AgentBStream(BaseAgent):

    def __init__(self, db_path, server_url, window_size=20, delay=2):
        super().__init__(server_url)
        self.db_path = db_path
        self.window_size = window_size
        self.delay = delay

    def run(self):

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", conn)
        conn.close()

        total_rows = len(df)

        for start in range(0, total_rows, self.window_size):

            end = start + self.window_size
            window_df = df.iloc[start:end]

            total = len(window_df)
            missing = window_df["value"].isna().sum()

            metrics = {
                "completeness": float(1 - missing / total),
                "missing_count": int(missing),
                "count": int(total)
            }

            print("Sending:", metrics)

            self.send_metrics("source_b", metrics)

            time.sleep(self.delay)


if __name__ == "__main__":

    agent = AgentBStream(
        "source_b.db",
        "http://127.0.0.1:8000",
        window_size=20,
        delay=2
    )

    agent.run()