"""API client for Obmenka course endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import API_URL, RATE_TYPE_CASH, RATE_TYPE_CASHLESS


class HaCartelApiError(Exception):
    """Raised when the Obmenka API request fails."""


@dataclass(frozen=True, slots=True)
class OfficeInfo:
    """Office metadata from the API."""

    office_id: int
    city: str
    is_first: bool


@dataclass(frozen=True, slots=True)
class RateQuote:
    """Single buy/sale quote for a currency."""

    currency: str
    rate_type: str
    buy: float | None
    sale: float | None


@dataclass(frozen=True, slots=True)
class OfficeRates:
    """Parsed rates for one office."""

    office_id: int
    city: str
    api_date: str | None
    quotes: tuple[RateQuote, ...]


def parse_rate_value(raw: str | float | int | None) -> float | None:
    """Parse EU-style decimal strings like '44,65' into floats."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _office_id_from_payload(item: dict[str, Any]) -> int | None:
    """Extract numeric office id from Id_otd field."""
    raw = item.get("Id_otd")
    if isinstance(raw, list) and raw:
        try:
            return int(raw[0])
        except (TypeError, ValueError):
            return None
    if isinstance(raw, (int, float, str)):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return None


def _quotes_from_list(
    rates: list[dict[str, Any]] | None, rate_type: str
) -> list[RateQuote]:
    """Convert API rate list into RateQuote objects."""
    result: list[RateQuote] = []
    if not rates:
        return result
    for entry in rates:
        currency = entry.get("val")
        if not currency:
            continue
        result.append(
            RateQuote(
                currency=str(currency).upper(),
                rate_type=rate_type,
                buy=parse_rate_value(entry.get("Buy")),
                sale=parse_rate_value(entry.get("Sale")),
            )
        )
    return result


def parse_offices(payload: dict[str, Any]) -> list[OfficeInfo]:
    """Parse office list from API payload."""
    data = payload.get("data") or []
    offices: list[OfficeInfo] = []
    for item in data:
        office_id = _office_id_from_payload(item)
        city = item.get("city")
        if office_id is None or not city:
            continue
        offices.append(
            OfficeInfo(
                office_id=office_id,
                city=str(city),
                is_first=bool(item.get("First")),
            )
        )
    return offices


def parse_office_rates(payload: dict[str, Any], office_id: int) -> OfficeRates:
    """Parse rates for a specific office id."""
    data = payload.get("data") or []
    for item in data:
        current_id = _office_id_from_payload(item)
        if current_id != office_id:
            continue
        quotes = _quotes_from_list(item.get("rates"), RATE_TYPE_CASH)
        quotes.extend(_quotes_from_list(item.get("ratesOpt"), RATE_TYPE_CASHLESS))
        return OfficeRates(
            office_id=office_id,
            city=str(item.get("city") or ""),
            api_date=item.get("Date"),
            quotes=tuple(quotes),
        )
    raise HaCartelApiError(f"Office {office_id} not found in API response")


async def async_fetch_payload(session: ClientSession) -> dict[str, Any]:
    """Fetch raw JSON payload from the Obmenka API."""
    try:
        async with session.get(API_URL, timeout=30) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except (ClientError, TimeoutError, ValueError) as err:
        raise HaCartelApiError(f"Failed to fetch rates: {err}") from err

    if not isinstance(payload, dict) or payload.get("result") != "OK":
        raise HaCartelApiError("Unexpected API response")
    return payload


async def async_get_offices(session: ClientSession) -> list[OfficeInfo]:
    """Fetch and return available offices."""
    payload = await async_fetch_payload(session)
    offices = parse_offices(payload)
    if not offices:
        raise HaCartelApiError("No offices returned by API")
    return offices


async def async_get_office_rates(
    session: ClientSession, office_id: int
) -> OfficeRates:
    """Fetch and return rates for one office."""
    payload = await async_fetch_payload(session)
    return parse_office_rates(payload, office_id)
