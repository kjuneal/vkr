# agent a
import pandas as pd
from sqlalchemy import create_engine
from agents.base_agent import BaseAgent


class AgentA(BaseAgent):

    def __init__(self, connection_string, server_url):
        super().__init__(server_url)
        self.engine = create_engine(connection_string)

    def compute_metrics(self):
        # df = pd.read_sql("SELECT * FROM data", self.engine)
        df = pd.read_sql("SELECT * FROM data ORDER BY timestamp", self.engine)

        return {
            "variance": float(df["value"].var()),
            "std": float(df["value"].std()),
            "count": len(df)
        }

    def run(self):
        metrics = self.compute_metrics()
        return self.send_metrics("source_a", metrics)


if __name__ == "__main__":
    conn = "postgresql://postgres:12345@localhost:5432/source_a.db"
    agent = AgentA(conn, "http://127.0.0.1:8000")
    print(agent.run())