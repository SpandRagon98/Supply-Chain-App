"""Deterministic normalization helpers preserving raw values separately."""

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

COUNTRY_ALIASES = {
    "TAIWAN": "TW",
    "REPUBLIC OF CHINA": "TW",
    "INDIA": "IN",
    "SINGAPORE": "SG",
    "JAPAN": "JP",
    "SOUTH KOREA": "KR",
    "KOREA": "KR",
    "CHINA": "CN",
    "MALAYSIA": "MY",
    "VIETNAM": "VN",
    "UNITED STATES": "US",
    "USA": "US",
}

UNIT_ALIASES = {
    "EACH": "EA",
    "EACHES": "EA",
    "PCS": "EA",
    "PIECES": "EA",
    "EA": "EA",
}


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_identifier(value: object) -> str:
    return normalize_text(value).upper()


def normalize_country(value: object) -> str:
    normalized = normalize_identifier(value)
    if len(normalized) == 2:
        return normalized
    return COUNTRY_ALIASES.get(normalized, normalized)


def normalize_unit(value: object) -> str:
    normalized = normalize_identifier(value)
    return UNIT_ALIASES.get(normalized, normalized)


def normalize_decimal(value: object, *, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def normalize_datetime(value: object, *, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return fallback
    else:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    for key in ("supplier_code", "site_code", "material_sku", "facility_code"):
        if key in normalized:
            normalized[key] = normalize_identifier(normalized[key])
    if "country" in normalized:
        normalized["country_code"] = normalize_country(normalized.pop("country"))
    elif "country_code" in normalized:
        normalized["country_code"] = normalize_country(normalized["country_code"])
    if "unit" in normalized:
        normalized["unit"] = normalize_unit(normalized["unit"])
    for key in ("location", "supplier_hint", "headline", "event", "reason"):
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalize_text(normalized[key])
    return normalized
