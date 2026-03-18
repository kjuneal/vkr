import pandas as pd
import time
from agents.base_agent import BaseAgent, compute_metrics


class AgentC(BaseAgent):

    def __init__(self, filepath, server_url, window_size=20, delay=2, selected_metrics=None):
        super().__init__(server_url)
        self.filepath = filepath
        self.window_size = window_size
        self.delay = delay
        self.selected_metrics = selected_metrics or ["mean", "std"]

    def run(self):
        df = pd.read_csv(self.filepath)

        for start in range(0, len(df), self.window_size):
            window_df = df.iloc[start:start + self.window_size]
            metrics   = compute_metrics(window_df["value"], self.selected_metrics)

            print(f"[Agent C] window {start}: {metrics}")
            self.send_metrics("source_c", metrics)
            time.sleep(self.delay)


if __name__ == "__main__":
    agent = AgentC(
        "data/source_c.csv",
        "http://127.0.0.1:8000",
        window_size=20,
        delay=2,
        selected_metrics=["mean", "std"]
    )

    agent.run()