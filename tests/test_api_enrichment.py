import pandas as pd

from app.config import get_settings
from app.processing.api_client import enrich_dataframe


def test_api_enrichment_uses_safe_fallback_without_network(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("COUNTRY_API_MODE", "mock")
    result = enrich_dataframe(pd.DataFrame({"country": ["ID", "SG"]}))
    assert set(result["api_status"]) == {"fallback_used"}
    assert set(result["currency"]) == {"IDR", "SGD"}
    get_settings.cache_clear()
