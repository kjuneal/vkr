# agent b // python -m agents.agent_b
import pandas as pd
import sqlite3
from agents.base_agent import BaseAgent, compute_metrics
import time

class AgentB(BaseAgent):

    def __init__(self, db_path, server_url, window_size=20, delay=2, selected_metrics=None):
        super().__init__(server_url)
        self.db_path = db_path
        self.window_size = window_size
        self.delay = delay
        self.selected_metrics = selected_metrics or ["completeness"]

    def run(self):

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", conn)
        conn.close()

        for start in range(0, len(df), self.window_size):
            window_df = df.iloc[start:start + self.window_size]
            metrics   = compute_metrics(window_df["value"], self.selected_metrics)

            print(f"[Agent B] window {start}: {metrics}")
            self.send_metrics("source_b", metrics)
            time.sleep(self.delay)


if __name__ == "__main__":

    agent = AgentB(
        "source_b.db",
        "http://127.0.0.1:8000",
        window_size=20,
        delay=2,
        selected_metrics=["completeness", "mean", "std"]
    )

    agent.run()