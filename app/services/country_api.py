from __future__ import annotations

import requests

from app.config import get_settings


LOCAL_COUNTRIES: dict[str, dict[str, str | None]] = {
    "ID": {"country_name": "Indonesia", "iso2": "ID", "iso3": "IDN", "region": "East Asia & Pacific", "income_level": "Upper middle income", "capital_city": "Jakarta", "latitude": "-6.1975", "longitude": "106.83"},
    "INDONESIA": {"country_name": "Indonesia", "iso2": "ID", "iso3": "IDN", "region": "East Asia & Pacific", "income_level": "Upper middle income", "capital_city": "Jakarta", "latitude": "-6.1975", "longitude": "106.83"},
    "SG": {"country_name": "Singapore", "iso2": "SG", "iso3": "SGP", "region": "East Asia & Pacific", "income_level": "High income", "capital_city": "Singapore", "latitude": "1.28941", "longitude": "103.85"},
    "MY": {"country_name": "Malaysia", "iso2": "MY", "iso3": "MYS", "region": "East Asia & Pacific", "income_level": "Upper middle income", "capital_city": "Kuala Lumpur", "latitude": "3.12433", "longitude": "101.684"},
    "PH": {"country_name": "Philippines", "iso2": "PH", "iso3": "PHL", "region": "East Asia & Pacific", "income_level": "Lower middle income", "capital_city": "Manila", "latitude": "14.5515", "longitude": "121.035"},
    "VN": {"country_name": "Vietnam", "iso2": "VN", "iso3": "VNM", "region": "East Asia & Pacific", "income_level": "Lower middle income", "capital_city": "Hanoi", "latitude": "21.0069", "longitude": "105.825"},
    "TH": {"country_name": "Thailand", "iso2": "TH", "iso3": "THA", "region": "East Asia & Pacific", "income_level": "Upper middle income", "capital_city": "Bangkok", "latitude": "13.7308", "longitude": "100.521"},
    "BR": {"country_name": "Brazil", "iso2": "BR", "iso3": "BRA", "region": "Latin America & Caribbean", "income_level": "Upper middle income", "capital_city": "Brasilia", "latitude": "-15.7801", "longitude": "-47.9292"},
}


def empty_country_metadata(value: str) -> dict[str, str | None]:
    return {
        "country_name": value,
        "iso2": None,
        "iso3": None,
        "region": None,
        "income_level": None,
        "capital_city": None,
        "latitude": None,
        "longitude": None,
    }


def parse_country_response(payload: object) -> dict[str, str | None]:
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        return empty_country_metadata("")
    item = payload[1][0]
    return {
        "country_name": item.get("name"),
        "iso2": item.get("iso2Code"),
        "iso3": item.get("id"),
        "region": (item.get("region") or {}).get("value"),
        "income_level": (item.get("incomeLevel") or {}).get("value"),
        "capital_city": item.get("capitalCity"),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
    }


def get_country_metadata(country_code_or_name: object) -> dict[str, str | None]:
    value = "" if country_code_or_name is None else str(country_code_or_name).strip()
    key = value.upper()
    if key in LOCAL_COUNTRIES:
        return LOCAL_COUNTRIES[key].copy()
    settings = get_settings()
    if settings.country_api_mode == "mock" or not value:
        return empty_country_metadata(value)
    try:
        response = requests.get(
            f"{settings.country_api_base_url}/country/{value}",
            params={"format": "json"},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        metadata = parse_country_response(response.json())
        return metadata if metadata.get("iso2") else empty_country_metadata(value)
    except requests.RequestException:
        return empty_country_metadata(value)
