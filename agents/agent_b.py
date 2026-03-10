# agent b
import pandas as pd
import sqlite3
from agents.base_agent import BaseAgent


class AgentB(BaseAgent):

    def __init__(self, db_path, server_url):
        super().__init__(server_url)
        self.db_path = db_path

    def compute_metrics(self):
        conn = sqlite3.connect(self.db_path)
        # df = pd.read_sql("SELECT * FROM data", conn)
        df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", conn)
        conn.close()

        total = len(df)
        missing = df["value"].isna().sum()

        return {
            "completeness": float(1 - missing / total),
            "missing_count": int(missing),
            "count": total
        }

    def run(self):
        metrics = self.compute_metrics()
        return self.send_metrics("source_b", metrics)


if __name__ == "__main__":
    agent = AgentB("source_b.db", "http://127.0.0.1:8000")
    print(agent.run())