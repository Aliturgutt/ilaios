import os
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

DEFAULT_MODEL = "anthropic/claude-sonnet-5"

# .env dosyasını proje kök klasöründe ara (src/core/agent.py'nin 2 üst klasörü)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class OpenRouterConfigError(Exception):
    """API anahtarı gibi yapılandırma bilgileri eksik veya geçersiz olduğunda yükseltilir."""


class OpenRouterResponseError(Exception):
    """OpenRouter yanıtı beklenen alanları içermediğinde yükseltilir."""


class OpenRouterAgent:
    def __init__(self) -> None:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise OpenRouterConfigError(
                "OPENROUTER_API_KEY bulunamadı! .env dosyasını kontrol et."
            )
        self.api_key: str = api_key
        self.base_url: str = "https://openrouter.ai/api/v1"
        self.model: str = os.getenv(
            "OPENROUTER_MODEL",
            DEFAULT_MODEL,
        )

    def chat(self, message: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 100
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()

        try:
            return str(result['choices'][0]['message']['content'])
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterResponseError(
                "OpenRouter yanıtı beklenen alanları içermiyor."
            ) from exc
