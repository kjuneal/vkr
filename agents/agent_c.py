import pandas as pd
import time
from agents.base_agent import BaseAgent


class AgentC(BaseAgent):

    def __init__(self, filepath, server_url, window_size=20, delay=2):
        super().__init__(server_url)
        self.filepath = filepath
        self.window_size = window_size
        self.delay = delay

    def run(self):
        df = pd.read_csv(self.filepath)

        total_rows = len(df)

        for start in range(0, total_rows, self.window_size):

            end = start + self.window_size
            window_df = df.iloc[start:end]

            mean = window_df["value"].mean()
            std = window_df["value"].std()

            metrics = {
                "mean": float(mean),
                "std": float(std)
            }

            print("Sending:", metrics)

            self.send_metrics("source_c", metrics)

            time.sleep(self.delay)


if __name__ == "__main__":
    agent = AgentC(
        "data/source_c.csv",
        "http://127.0.0.1:8000",
        window_size=20,
        delay=2
    )

    agent.run()