import pandas as pd
import requests

from app.chatbot.llm_client import AIProviderConfig, SpreadsheetAssistantClient
from app.config import get_settings
from app.processing.profiler import profile_dataframe


def test_llm_client_uses_rule_based_fallback_without_api_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profile = profile_dataframe(pd.DataFrame({"due_date": ["bad-date"], "amount": ["1,200"]}), "sample.csv", "csv")

    client = SpreadsheetAssistantClient()
    review = client.review_profile(profile)
    plan = client.recommend_plan(profile)

    assert "Saya sudah membaca `sample.csv`" in review
    assert [action.action_name for action in plan.actions]
    assert all(action.action_name != "exec_python_code" for action in plan.actions)
    get_settings.cache_clear()


def test_ai_provider_model_listing_uses_models_endpoint(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "model-b"}, {"id": "model-a"}]}

    def fake_get(url, headers, timeout):
        assert url == "https://example.test/v1/models"
        assert headers["Authorization"] == "Bearer test-key"
        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)
    client = SpreadsheetAssistantClient(
        config=AIProviderConfig(
            provider="openai_compatible",
            api_key="test-key",
            base_url="https://example.test/v1",
            model="model-a",
        )
    )

    ok, message, models = client.test_connection()

    assert ok is True
    assert "model ditemukan" in message
    assert models == ["model-a", "model-b"]


def test_openrouter_provider_uses_bearer_header_and_openrouter_models_url(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "openrouter/free"}]}

    def fake_get(url, headers, timeout):
        assert url == "https://openrouter.ai/api/v1/models"
        assert headers["Authorization"] == "Bearer sk-or-test"
        assert headers["X-Title"] == "AI Spreadsheet Automation Assistant"
        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)
    client = SpreadsheetAssistantClient(
        config=AIProviderConfig(
            provider="openrouter",
            api_key=" sk-or-test ",
            base_url="ignored",
            model="openrouter/free",
        )
    )

    ok, _, models = client.test_connection()

    assert ok is True
    assert models == ["openrouter/free"]
