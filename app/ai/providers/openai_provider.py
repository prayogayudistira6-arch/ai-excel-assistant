from __future__ import annotations

from urllib.parse import urljoin

import requests

from app.ai.providers.base import ProviderConfig


def _join_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


class OpenAIProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        if not self.config.base_url:
            self.config.base_url = "https://api.openai.com/v1"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.api_key.strip()}", "Content-Type": "application/json"}

    def list_models(self) -> list[str]:
        if not self.config.api_key.strip():
            return []
        response = requests.get(_join_url(self.config.base_url, "models"), headers=self._headers(), timeout=15)
        response.raise_for_status()
        payload = response.json()
        return sorted(item["id"] for item in payload.get("data", []) if isinstance(item, dict) and item.get("id"))

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.config.provider == "openai_compatible":
            return self._chat_completions(system_prompt, user_prompt)
        response = requests.post(
            _join_url(self.config.base_url, "responses"),
            headers=self._headers(),
            json={
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        chunks: list[str] = []
        for item in payload.get("output", []):
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(content, dict) and content.get("text"):
                    chunks.append(str(content["text"]))
        return "\n".join(chunks)

    def _chat_completions(self, system_prompt: str, user_prompt: str) -> str:
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
            return False, "API key belum diisi.", []
        try:
            models = self.list_models()
            return True, f"Koneksi OpenAI-compatible berhasil. {len(models)} model ditemukan.", models
        except requests.RequestException as exc:
            return False, f"Koneksi gagal: {exc}", []
