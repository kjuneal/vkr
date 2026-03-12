import requests
from datetime import datetime


class BaseAgent:

    def __init__(self, server_url):
        self.server_url = server_url

    def send_metrics(self, source_name, metrics):

        payload = {
            "source": source_name,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }

        response = requests.post(
            f"{self.server_url}/metrics/",
            json=payload
        )

        print("Payload:", payload)
        print("Server response:", response.status_code)
        print("Server message:", response.text)