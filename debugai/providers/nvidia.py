import os
from .base import AIProvider


class NvidiaProvider(AIProvider):

    MODEL = "mistralai/mistral-large-3-675b-instruct-2512"
    BASE_URL = "https://integrate.api.nvidia.com/v1"

    def name(self) -> str:
        return "NVIDIA"

    def is_available(self) -> bool:
        return bool(os.getenv("NVIDIA_API_KEY"))

    def analyze(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            base_url=self.BASE_URL,
            api_key=os.getenv("NVIDIA_API_KEY")
        )

        completion = client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": "You are an expert debugging assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )

        return completion.choices[0].message.content
