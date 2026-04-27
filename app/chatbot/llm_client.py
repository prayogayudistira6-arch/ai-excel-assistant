from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urljoin

import requests

from app.chatbot.action_parser import recommended_actions, sanitize_cleaning_plan
from app.chatbot.prompt_builder import build_natural_review, build_review_prompt
from app.config import get_settings
from app.models import CleaningPlan, DataProfile


SYSTEM_PROMPT = (
    "You are a safe spreadsheet automation assistant. You review uploaded tabular data profiles "
    "and recommend cleaning actions. Do not write code. Only recommend actions from the allowed "
    "action list. Be conservative. Do not invent columns. Ask the user before executing destructive changes."
)


@dataclass(frozen=True)
class AIProviderConfig:
    provider: str = "rule_based"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-5.5"

    @property
    def enabled(self) -> bool:
        return self.provider != "rule_based" and bool(self.api_key.strip())

    @property
    def normalized_base_url(self) -> str:
        if self.provider == "openrouter":
            return "https://openrouter.ai/api/v1"
        return self.base_url


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


class SpreadsheetAssistantClient:
    def __init__(self, config: AIProviderConfig | None = None) -> None:
        self.settings = get_settings()
        self.config = config or AIProviderConfig(
            provider=self.settings.ai_provider,
            api_key=self.settings.ai_api_key or self.settings.openai_api_key,
            base_url=self.settings.ai_base_url,
            model=self.settings.ai_model or self.settings.openai_model,
        )

    def review_profile(self, profile: DataProfile) -> str:
        if not self.config.enabled:
            return build_natural_review(profile)
        try:
            text = self._call_text(SYSTEM_PROMPT, build_review_prompt(profile))
            if isinstance(text, str) and text.strip():
                return text
        except (requests.RequestException, ValueError):
            pass
        return build_natural_review(profile)

    def recommend_plan(self, profile: DataProfile) -> CleaningPlan:
        if not self.config.enabled:
            return CleaningPlan(actions=recommended_actions(profile), user_instruction="fallback rule-based plan")
        try:
            text = self._call_text(SYSTEM_PROMPT + " Return only JSON matching CleaningPlan.", build_review_prompt(profile))
            data = json.loads(text)
            plan = sanitize_cleaning_plan(CleaningPlan.model_validate(data))
            if plan.actions:
                return plan
        except (requests.RequestException, ValueError, TypeError):
            pass
        return CleaningPlan(actions=recommended_actions(profile), user_instruction="fallback rule-based plan")

    def list_models(self) -> list[str]:
        if not self.config.enabled:
            return []
        if not self.config.api_key.strip():
            raise ValueError("API key kosong. Isi API key terlebih dahulu.")
        response = requests.get(
            _join_url(self.config.normalized_base_url, "models"),
            headers=self._headers(),
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", []) if isinstance(payload, dict) else []
        models = [item.get("id") for item in data if isinstance(item, dict) and item.get("id")]
        return sorted(set(models))

    def test_connection(self) -> tuple[bool, str, list[str]]:
        if not self.config.enabled:
            return False, "API key belum diisi atau provider masih rule-based.", []
        try:
            models = self.list_models()
            if models:
                return True, f"Koneksi berhasil. {len(models)} model ditemukan.", models
            return True, "Koneksi berhasil, tetapi daftar model kosong. Anda tetap bisa mengetik model manual.", []
        except (requests.RequestException, ValueError) as exc:
            return False, f"Koneksi gagal: {exc}", []

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key.strip()}",
            "Content-Type": "application/json",
        }
        if self.config.provider == "openrouter":
            headers["HTTP-Referer"] = "http://localhost:8501"
            headers["X-Title"] = "AI Spreadsheet Automation Assistant"
        return headers

    def _call_text(self, system_prompt: str, user_prompt: str) -> str:
        if self.config.provider in {"openai_compatible", "openrouter"}:
            return self._call_chat_completions(system_prompt, user_prompt)
        return self._call_responses(system_prompt, user_prompt)

    def _call_responses(self, system_prompt: str, user_prompt: str) -> str:
        response = requests.post(
            _join_url(self.config.normalized_base_url, "responses"),
            headers=self._headers(),
            json={
                "model": self.config.model,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("output_text")
        if isinstance(text, str):
            return text
        output = payload.get("output", [])
        chunks: list[str] = []
        for item in output if isinstance(output, list) else []:
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(content, dict) and content.get("text"):
                    chunks.append(str(content["text"]))
        return "\n".join(chunks)

    def _call_chat_completions(self, system_prompt: str, user_prompt: str) -> str:
        response = requests.post(
            _join_url(self.config.normalized_base_url, "chat/completions"),
            headers=self._headers(),
            json={
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices", [])
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str):
                return content
        return ""
