from __future__ import annotations

from app.ai.providers.base import ProviderConfig


class MockProvider:
    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig(provider="mock", model="mock-rule-based")

    def list_models(self) -> list[str]:
        return ["mock-rule-based"]

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "{}"

    def test_connection(self) -> tuple[bool, str, list[str]]:
        return True, "Mock provider aktif. Tidak membutuhkan API key.", self.list_models()
