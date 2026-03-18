# # agent a
import os
os.environ["PGCLIENTENCODING"] = "UTF8"

import pandas as pd
import time
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from agents.base_agent import BaseAgent, compute_metrics


class AgentA(BaseAgent):

    def __init__(self, db_name, server_url, window_size=20, delay=2, selected_metrics=None):
        super().__init__(server_url)
        url = URL.create(
            drivername="postgresql+psycopg2",
            username="postgres",
            password="12345",
            host="localhost",
            port=5432,
            database=db_name,
        )
        self.engine = create_engine(url)
        self.window_size = window_size
        self.delay = delay
        self.selected_metrics = selected_metrics or ["mean", "std"]

    def run(self):
        df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", self.engine)

        for start in range(0, len(df), self.window_size):
            window_df = df.iloc[start:start + self.window_size]
            metrics   = compute_metrics(window_df["value"], self.selected_metrics)

            print(f"[Agent A] window {start}: {metrics}")
            self.send_metrics("source_a", metrics)
            time.sleep(self.delay)


if __name__ == "__main__":

    agent = AgentA(
        db_name="source_a.db",
        server_url="http://127.0.0.1:8000",
        window_size=20,
        delay=2,
        selected_metrics=["mean", "std", "median", "iqr"]
    )

    agent.run()