from __future__ import annotations

from app.ai.providers.base import ProviderConfig
from app.ai.providers.mock_provider import MockProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider


STATIC_MODELS = {
    "mock": ["mock-rule-based"],
    "openai": ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini"],
    "openai_compatible": ["gpt-5.4-mini", "qwen/qwen3-coder", "deepseek/deepseek-chat"],
    "openrouter": ["openrouter/free", "openai/gpt-oss-20b:free", "deepseek/deepseek-chat-v3.1:free"],
}


def create_provider(config: ProviderConfig):
    if config.provider == "openrouter":
        return OpenRouterProvider(config)
    if config.provider in {"openai", "openai_compatible"}:
        return OpenAIProvider(config)
    return MockProvider(config)


def default_models(provider: str) -> list[str]:
    return STATIC_MODELS.get(provider, STATIC_MODELS["mock"])
