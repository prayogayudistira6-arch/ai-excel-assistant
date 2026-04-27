from __future__ import annotations

import requests

from app.ai.providers.base import ProviderConfig
from app.ai.providers.openai_provider import _join_url


class OpenRouterProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.config.base_url = self.config.base_url or "https://openrouter.ai/api/v1"
        if not self.config.model or self.config.model == "mock":
            self.config.model = "openrouter/free"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Excel AI Agent Assistant",
        }

    def list_models(self) -> list[str]:
        if not self.config.api_key.strip():
            return []
        response = requests.get(_join_url(self.config.base_url, "models"), headers=self._headers(), timeout=15)
        response.raise_for_status()
        payload = response.json()
        return sorted(item["id"] for item in payload.get("data", []) if isinstance(item, dict) and item.get("id"))

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = requests.post(
            _join_url(self.config.base_url, "chat/completions"),
            headers=self._headers(),
            json={
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices", [])
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
        return ""

    def test_connection(self) -> tuple[bool, str, list[str]]:
        if not self.config.api_key.strip():
            return False, "API key belum diisi. OpenRouter key biasanya diawali sk-or-...", []
        try:
            models = self.list_models()
            return True, f"Koneksi OpenRouter berhasil. {len(models)} model ditemukan.", models
        except requests.RequestException as exc:
            return False, f"Koneksi OpenRouter gagal: {exc}", []
