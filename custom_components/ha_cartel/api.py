"""API client for Obmenka course endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .const import (
    API_URL,
    RATE_TYPE_CASH,
    RATE_TYPE_CASHLESS,
    RATE_TYPE_CROSS_CASH,
    RATE_TYPE_CROSS_CASHLESS,
)

_LOGGER = logging.getLogger(__name__)

# Separate connect/read limits so blackholed :5001 fails with a clear timeout,
# not a blank "Failed to fetch rates:" (TimeoutError stringifies to "").
REQUEST_TIMEOUT = ClientTimeout(total=45, connect=20, sock_connect=20, sock_read=30)
FETCH_ATTEMPTS = 3
FETCH_RETRY_DELAY = 2.0


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


def _office_ids_from_payload(item: dict[str, Any]) -> list[int]:
    """Extract all numeric office ids from Id_otd field."""
    raw = item.get("Id_otd")
    values: list[Any]
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, (int, float, str)):
        values = [raw]
    else:
        return []

    ids: list[int] = []
    for value in values:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _office_id_from_payload(item: dict[str, Any]) -> int | None:
    """Extract primary numeric office id from Id_otd field."""
    ids = _office_ids_from_payload(item)
    return ids[0] if ids else None


def _item_matches_office(item: dict[str, Any], office_id: int) -> bool:
    """Return True if the payload row belongs to office_id."""
    return office_id in _office_ids_from_payload(item)


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
    """Parse unique offices from API payload.

    De-duplicate by office id, preferring rows marked First.
    """
    data = payload.get("data") or []
    by_id: dict[int, OfficeInfo] = {}
    for item in data:
        office_id = _office_id_from_payload(item)
        city = item.get("city")
        if office_id is None or not city:
            continue
        candidate = OfficeInfo(
            office_id=office_id,
            city=str(city),
            is_first=bool(item.get("First")),
        )
        existing = by_id.get(office_id)
        if existing is None or (candidate.is_first and not existing.is_first):
            by_id[office_id] = candidate
    return list(by_id.values())


def _quotes_for_item(item: dict[str, Any]) -> list[RateQuote]:
    """Build all quote types for one office payload row."""
    quotes = _quotes_from_list(item.get("rates"), RATE_TYPE_CASH)
    quotes.extend(_quotes_from_list(item.get("ratesOpt"), RATE_TYPE_CASHLESS))
    quotes.extend(
        _quotes_from_list(item.get("ratesCross"), RATE_TYPE_CROSS_CASH, cross=True)
    )
    quotes.extend(
        _quotes_from_list(
            item.get("ratesCrossOpt"), RATE_TYPE_CROSS_CASHLESS, cross=True
        )
    )
    return quotes


def parse_office_rates(payload: dict[str, Any], office_id: int) -> OfficeRates:
    """Parse rates for a specific office id.

    The API can return multiple rows for the same Id_otd (e.g. Poltava). Prefer the
    row marked First, then the row with the most quotes.
    """
    data = payload.get("data") or []
    matches = [item for item in data if _item_matches_office(item, office_id)]
    if not matches:
        raise HaCartelApiError(f"Office {office_id} not found in API response")

    matches.sort(
        key=lambda item: (
            1 if item.get("First") else 0,
            len(_quotes_for_item(item)),
        ),
        reverse=True,
    )
    item = matches[0]
    quotes = _quotes_for_item(item)
    return OfficeRates(
        office_id=office_id,
        city=str(item.get("city") or ""),
        api_date=item.get("Date"),
        quotes=tuple(quotes),
    )


def _format_request_error(err: BaseException) -> str:
    """Build a useful message even when str(err) is empty (e.g. TimeoutError)."""
    if isinstance(err, (TimeoutError, asyncio.TimeoutError)):
        return (
            "Timed out reaching api.obmenka.dn.ua:5001 "
            "(connection stalled or server slow; will retry)."
        )
    if isinstance(err, ClientResponseError):
        detail = (err.message or str(err) or "").strip()
        return f"HTTP {err.status} from {API_URL}" + (f": {detail}" if detail else "")

    text = str(err).strip()
    if not text:
        text = type(err).__name__

    cause = err.__cause__ or getattr(err, "os_error", None)
    if cause is not None:
        cause_text = str(cause).strip() or type(cause).__name__
        if cause_text and cause_text not in text:
            text = f"{text} ({cause_text})"
    return text


async def async_fetch_payload(session: ClientSession) -> dict[str, Any]:
    """Fetch raw JSON payload from the Obmenka API (with short retries)."""
    headers = {
        "Accept": "application/json, */*",
        "Referer": "https://cartel.in.ua/",
        "Origin": "https://cartel.in.ua",
    }
    last_error: BaseException | None = None

    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            async with session.get(
                API_URL, headers=headers, timeout=REQUEST_TIMEOUT
            ) as response:
                body = await response.text()
                if response.status >= 400:
                    raise HaCartelApiError(
                        f"HTTP {response.status} from {API_URL}: {body[:200]!r}"
                    )
                try:
                    payload = json.loads(body) if body else None
                except json.JSONDecodeError as err:
                    raise HaCartelApiError(
                        f"Invalid JSON from API: {err}; body={body[:200]!r}"
                    ) from err
        except HaCartelApiError as err:
            last_error = err
        except (ClientError, TimeoutError, asyncio.TimeoutError, ValueError) as err:
            last_error = err
            _LOGGER.debug(
                "Obmenka fetch attempt %s/%s failed: %s: %s",
                attempt,
                FETCH_ATTEMPTS,
                type(err).__name__,
                _format_request_error(err),
            )
        else:
            if not isinstance(payload, dict) or payload.get("result") != "OK":
                raise HaCartelApiError("Unexpected API response")
            return payload

        if attempt < FETCH_ATTEMPTS:
            await asyncio.sleep(FETCH_RETRY_DELAY)

    assert last_error is not None
    if isinstance(last_error, HaCartelApiError):
        raise last_error
    raise HaCartelApiError(
        f"Failed to fetch rates: {_format_request_error(last_error)}"
    ) from last_error


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
