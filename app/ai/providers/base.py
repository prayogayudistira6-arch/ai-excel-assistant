from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderConfig:
    provider: str = "mock"
    api_key: str = ""
    base_url: str = ""
    model: str = "mock"
    temperature: float = 0.2
    max_tokens: int = 1200


class AIProvider(Protocol):
    config: ProviderConfig

    def list_models(self) -> list[str]:
        ...

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...

    def test_connection(self) -> tuple[bool, str, list[str]]:
        ...
