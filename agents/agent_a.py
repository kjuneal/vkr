# # agent a
import pandas as pd
from sqlalchemy import create_engine
from agents.base_agent import BaseAgent


# class AgentA(BaseAgent):

#     def __init__(self, connection_string, server_url):
#         super().__init__(server_url)
#         self.engine = create_engine(connection_string)

#     def compute_metrics(self):
#         # df = pd.read_sql("SELECT * FROM data", self.engine)
#         df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", self.engine)

#         return {
#             "variance": float(df["value"].var()),
#             "std": float(df["value"].std()),
#             "count": len(df)
#         }

#     def run(self):
#         metrics = self.compute_metrics()
#         return self.send_metrics("source_a", metrics)


# if __name__ == "__main__":
#     conn = "postgresql://postgres:12345@localhost:5432/source_a.db"
#     agent = AgentA(conn, "http://127.0.0.1:8000")
#     print(agent.run())

# agent_a_stream.py

import time
from sqlalchemy.engine import URL


class AgentA(BaseAgent):

    def __init__(self, db_name, server_url, window_size=20, delay=2):
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

    def run(self):

        df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", self.engine)

        total_rows = len(df)

        for start in range(0, total_rows, self.window_size):

            end = start + self.window_size
            window_df = df.iloc[start:end]

            variance = window_df["value"].var()
            std = window_df["value"].std()

            # metrics = {
            #     "mean": float(window_df["value"].mean()),
            #     "std": float(std),
            #     "count": len(window_df)
            # }
            metrics = {
                "mean": float(window_df["value"].mean()),
                "std": float(window_df["value"].std()),
                "count": len(window_df)
            }

            print("Sending:", metrics)

            self.send_metrics("source_a", metrics)

            time.sleep(self.delay)


if __name__ == "__main__":

    agent = AgentA(
        db_name="source_a.db",
        server_url="http://127.0.0.1:8000",
        window_size=20,
        delay=2
    )

    agent.run()