"""Constants for the HA Cartel integration."""

from datetime import timedelta

DOMAIN = "ha_cartel"

CARTEL_RATES_URL = "https://cartel.in.ua/includes/admin_content_funcs.php"

DEFAULT_OFFICE_ID = 37
DEFAULT_CITY = "Харьков"
INTEGRATION_TITLE = "Cartel Kharkiv #1 (458-1)"

UPDATE_INTERVAL = timedelta(hours=1)

CONF_CITY = "city"
CONF_OFFICE_ID = "office_id"

RATE_TYPE_CASH = "cash"
RATE_TYPE_CASHLESS = "cashless"
RATE_TYPE_CROSS_CASH = "cross_cash"
RATE_TYPE_CROSS_CASHLESS = "cross_cashless"

# ISO codes from API `val` / `to_val` → display names.
CURRENCY_NAMES: dict[str, str] = {
    "AED": "UAE Dirham",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "CNY": "Chinese Yuan",
    "CZK": "Czech Koruna",
    "DKK": "Danish Krone",
    "EGP": "Egyptian Pound",
    "EUR": "Euro",
    "GBP": "British Pound",
    "GEL": "Georgian Lari",
    "HUF": "Hungarian Forint",
    "MDL": "Moldovan Leu",
    "NOK": "Norwegian Krone",
    "PLN": "Polish Zloty",
    "RON": "Romanian Leu",
    "SEK": "Swedish Krona",
    "TRY": "Turkish Lira",
    "UAH": "Ukrainian Hryvnia",
    "USD": "US Dollar",
}

CURRENCY_ICONS: dict[str, str] = {
    "EUR": "mdi:currency-eur",
    "GBP": "mdi:currency-gbp",
    "TRY": "mdi:currency-try",
    "CNY": "mdi:currency-cny",
    "JPY": "mdi:currency-jpy",
    "RUB": "mdi:currency-rub",
    "INR": "mdi:currency-inr",
    "KRW": "mdi:currency-krw",
    "BRL": "mdi:currency-brl",
    "USD": "mdi:currency-usd",
    "UAH": "mdi:currency-uah",
}

ATTR_CITY = "city"
ATTR_OFFICE_ID = "office_id"
ATTR_CURRENCY = "currency"
ATTR_CURRENCY_NAME = "currency_name"
ATTR_TO_CURRENCY = "to_currency"
ATTR_TO_CURRENCY_NAME = "to_currency_name"
ATTR_SIDE = "side"
ATTR_OPT = "opt"
ATTR_API_DATE = "api_date"


def currency_name(code: str | None) -> str | None:
    """Return a human-readable name for an ISO currency code."""
    if not code:
        return None
    normalized = code.upper()
    return CURRENCY_NAMES.get(normalized, normalized)
