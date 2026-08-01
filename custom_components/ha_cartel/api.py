"""API client for Obmenka course endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    API_URL,
    RATE_TYPE_CASH,
    RATE_TYPE_CASHLESS,
    RATE_TYPE_CROSS_CASH,
    RATE_TYPE_CROSS_CASHLESS,
)


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
    """Single buy/sale quote for a currency or cross pair."""

    currency: str
    rate_type: str
    buy: float | None
    sale: float | None
    to_currency: str | None = None


@dataclass(frozen=True, slots=True)
class CurrencyRate:
    """Merged cash + opt rates for one currency or cross pair."""

    currency: str
    to_currency: str | None
    buy: float | None
    sell: float | None
    buy_opt: float | None
    sell_opt: float | None

    @property
    def key(self) -> str:
        """Stable id fragment."""
        if self.to_currency:
            return f"{self.currency.lower()}_{self.to_currency.lower()}"
        return self.currency.lower()

    @property
    def label(self) -> str:
        """Sensor name: USD or EUR/USD."""
        if self.to_currency:
            return f"{self.currency}/{self.to_currency}"
        return self.currency

    @property
    def primary(self) -> float | None:
        """Main state: prefer cash buy, then opt buy, then sell."""
        for value in (self.buy, self.buy_opt, self.sell, self.sell_opt):
            if value is not None:
                return value
        return None


@dataclass(frozen=True, slots=True)
class OfficeRates:
    """Parsed rates for one office."""

    office_id: int
    city: str
    api_date: str | None
    quotes: tuple[RateQuote, ...]

    @property
    def currencies(self) -> tuple[CurrencyRate, ...]:
        """One merged rate row per currency / cross pair."""
        return merge_quotes(self.quotes)


def merge_quotes(quotes: tuple[RateQuote, ...] | list[RateQuote]) -> tuple[CurrencyRate, ...]:
    """Merge cash and opt quotes into one CurrencyRate per pair."""
    buckets: dict[tuple[str, str | None], dict[str, float | None]] = {}
    order: list[tuple[str, str | None]] = []

    for quote in quotes:
        key = (quote.currency, quote.to_currency)
        if key not in buckets:
            buckets[key] = {
                "buy": None,
                "sell": None,
                "buy_opt": None,
                "sell_opt": None,
            }
            order.append(key)

        bucket = buckets[key]
        is_opt = quote.rate_type in (
            RATE_TYPE_CASHLESS,
            RATE_TYPE_CROSS_CASHLESS,
        )
        if is_opt:
            bucket["buy_opt"] = quote.buy
            bucket["sell_opt"] = quote.sale
        else:
            bucket["buy"] = quote.buy
            bucket["sell"] = quote.sale

    merged: list[CurrencyRate] = []
    for currency, to_currency in order:
        values = buckets[(currency, to_currency)]
        merged.append(
            CurrencyRate(
                currency=currency,
                to_currency=to_currency,
                buy=values["buy"],
                sell=values["sell"],
                buy_opt=values["buy_opt"],
                sell_opt=values["sell_opt"],
            )
        )
    return tuple(merged)


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
    rates: list[dict[str, Any]] | None,
    rate_type: str,
    *,
    cross: bool = False,
) -> list[RateQuote]:
    """Convert API rate list into RateQuote objects."""
    result: list[RateQuote] = []
    if not rates:
        return result
    for entry in rates:
        currency = entry.get("val")
        if not currency:
            continue
        to_currency: str | None = None
        if cross:
            raw_to = entry.get("to_val")
            if not raw_to:
                continue
            to_currency = str(raw_to).upper()
        result.append(
            RateQuote(
                currency=str(currency).upper(),
                rate_type=rate_type,
                buy=parse_rate_value(entry.get("Buy")),
                sale=parse_rate_value(entry.get("Sale")),
                to_currency=to_currency,
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
        quotes.extend(
            _quotes_from_list(
                item.get("ratesCross"), RATE_TYPE_CROSS_CASH, cross=True
            )
        )
        quotes.extend(
            _quotes_from_list(
                item.get("ratesCrossOpt"), RATE_TYPE_CROSS_CASHLESS, cross=True
            )
        )
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
