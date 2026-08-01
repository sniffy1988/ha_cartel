"""Constants for the HA Cartel integration."""

from datetime import timedelta

DOMAIN = "ha_cartel"

API_URL = "https://api.obmenka.dn.ua:5001/course?org=2"

UPDATE_INTERVAL = timedelta(hours=1)

CONF_CITY = "city"
CONF_OFFICE_ID = "office_id"

RATE_TYPE_CASH = "cash"
RATE_TYPE_CASHLESS = "cashless"

ATTR_CITY = "city"
ATTR_OFFICE_ID = "office_id"
ATTR_RATE_TYPE = "rate_type"
ATTR_CURRENCY = "currency"
ATTR_SIDE = "side"
ATTR_API_DATE = "api_date"
