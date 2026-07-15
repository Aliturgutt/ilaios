import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını proje kök klasöründe ara (src/core/agent.py'nin 2 üst klasörü)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class OpenRouterAgent:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "deepseek/deepseek-chat"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY bulunamadı! .env dosyasını kontrol et.")

    def chat(self, message):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 100
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Hata: {str(e)}"
