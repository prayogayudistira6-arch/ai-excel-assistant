from __future__ import annotations

import logging

import pandas as pd
import requests

from app.config import get_settings


LOGGER = logging.getLogger(__name__)

COUNTRY_FALLBACK = {
    "ID": {"normalized_country_name": "Indonesia", "region": "East Asia & Pacific", "currency": "IDR"},
    "INDONESIA": {"normalized_country_name": "Indonesia", "region": "East Asia & Pacific", "currency": "IDR"},
    "SG": {"normalized_country_name": "Singapore", "region": "East Asia & Pacific", "currency": "SGD"},
    "SINGAPORE": {"normalized_country_name": "Singapore", "region": "East Asia & Pacific", "currency": "SGD"},
    "US": {"normalized_country_name": "United States", "region": "North America", "currency": "USD"},
    "USA": {"normalized_country_name": "United States", "region": "North America", "currency": "USD"},
    "MY": {"normalized_country_name": "Malaysia", "region": "East Asia & Pacific", "currency": "MYR"},
    "PH": {"normalized_country_name": "Philippines", "region": "East Asia & Pacific", "currency": "PHP"},
    "TH": {"normalized_country_name": "Thailand", "region": "East Asia & Pacific", "currency": "THB"},
    "VN": {"normalized_country_name": "Vietnam", "region": "East Asia & Pacific", "currency": "VND"},
}


def _empty(value: object, status: str, detail: str) -> dict[str, object]:
    return {
        "country": "" if pd.isna(value) else str(value),
        "normalized_country_name": None,
        "region": None,
        "currency": None,
        "api_status": status,
        "detail": detail,
    }


def enrich_country(value: object) -> dict[str, object]:
    settings = get_settings()
    key = "" if pd.isna(value) else str(value).strip()
    if not key:
        return _empty(value, "skipped", "blank country")
    fallback = COUNTRY_FALLBACK.get(key.upper())
    if settings.country_api_mode == "mock":
        LOGGER.info("API called: country enrichment mock fallback")
        if fallback:
            return {"country": key, **fallback, "api_status": "fallback_used", "detail": "mock fallback"}
        return _empty(value, "fallback_missing", "country not in fallback mapping")
    try:
        LOGGER.info("API called: World Bank country API")
        response = requests.get(
            f"{settings.country_api_base_url}/country/{key}",
            params={"format": "json"},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        item = payload[1][0] if isinstance(payload, list) and len(payload) > 1 and payload[1] else None
        if item:
            LOGGER.info("API success: World Bank country API")
            return {
                "country": key,
                "normalized_country_name": item.get("name"),
                "region": (item.get("region") or {}).get("value"),
                "currency": fallback.get("currency") if fallback else None,
                "api_status": "success",
                "detail": "worldbank",
            }
    except (requests.RequestException, ValueError, TypeError, IndexError) as exc:
        LOGGER.warning("API failure: fallback used: %s", exc)
    if fallback:
        return {"country": key, **fallback, "api_status": "fallback_used", "detail": "api failed or no match"}
    return _empty(value, "fallback_missing", "api failed and no fallback mapping")


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    country_columns = [col for col in df.columns if str(col).lower() in {"country", "country_code", "country_name"}]
    if not country_columns:
        return pd.DataFrame(columns=["country", "normalized_country_name", "region", "currency", "api_status", "detail"])
    col = country_columns[0]
    rows = [enrich_country(value) for value in sorted(df[col].dropna().astype(str).unique())]
    return pd.DataFrame(rows)
