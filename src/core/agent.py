import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

DEFAULT_MODEL = "anthropic/claude-sonnet-5"

# .env dosyasini proje kocke klasorunda ara (src/core/agent.py'nin 2 ust klasoru)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class OpenRouterConfigError(Exception):
    """API anahtarı gibi yapilandirmalari eksik veya gecerli olmadiginda yukselir."""


class OpenRouterResponseError(Exception):
    """OpenRouter response'u beklenen alanlari icermediğinde yükselir."""


class OpenRouterAgent:
    def __init__(self) -> None:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise OpenRouterConfigError(
                "OPENROUTER_API_KEY bulunamadi! .env dosyasini kontrol et."
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

        data: dict[str, Any] = {
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
