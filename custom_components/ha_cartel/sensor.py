"""Sensor platform for HA Cartel."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import OfficeRates, RateQuote
from .const import (
    ATTR_API_DATE,
    ATTR_CITY,
    ATTR_CURRENCY,
    ATTR_OFFICE_ID,
    ATTR_RATE_TYPE,
    ATTR_SIDE,
    DOMAIN,
    RATE_TYPE_CASH,
)
from .coordinator import HaCartelCoordinator

SIDE_BUY = "buy"
SIDE_SALE = "sale"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HA Cartel sensors from a config entry."""
    coordinator: HaCartelCoordinator = entry.runtime_data
    data = coordinator.data
    entities: list[HaCartelRateSensor] = []

    for quote in data.quotes:
        if quote.buy is not None:
            entities.append(
                HaCartelRateSensor(coordinator, quote, SIDE_BUY)
            )
        if quote.sale is not None:
            entities.append(
                HaCartelRateSensor(coordinator, quote, SIDE_SALE)
            )

    async_add_entities(entities)


class HaCartelRateSensor(CoordinatorEntity[HaCartelCoordinator], SensorEntity):
    """Buy or sale rate sensor for one currency."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "UAH"
    _attr_icon = "mdi:currency-usd"

    def __init__(
        self,
        coordinator: HaCartelCoordinator,
        quote: RateQuote,
        side: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._currency = quote.currency
        self._rate_type = quote.rate_type
        self._side = side
        office_id = coordinator.office_id
        self._attr_unique_id = (
            f"{DOMAIN}_{office_id}_{quote.rate_type}_{quote.currency.lower()}_{side}"
        )
        rate_label = "Cash" if quote.rate_type == RATE_TYPE_CASH else "Cashless"
        side_label = "Buy" if side == SIDE_BUY else "Sale"
        self._attr_name = f"{rate_label} {quote.currency} {side_label}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(office_id))},
            name=f"Obmenka {coordinator.data.city} ({office_id})",
            manufacturer="Obmenka",
            model="Exchange rates",
            configuration_url="https://obmenka.dn.ua",
        )

    def _current_quote(self) -> RateQuote | None:
        """Find the matching quote in the latest coordinator data."""
        data: OfficeRates = self.coordinator.data
        for quote in data.quotes:
            if (
                quote.currency == self._currency
                and quote.rate_type == self._rate_type
            ):
                return quote
        return None

    @property
    def native_value(self) -> float | None:
        """Return the current rate."""
        quote = self._current_quote()
        if quote is None:
            return None
        return quote.buy if self._side == SIDE_BUY else quote.sale

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Return extra attributes."""
        data = self.coordinator.data
        return {
            ATTR_CITY: data.city,
            ATTR_OFFICE_ID: data.office_id,
            ATTR_RATE_TYPE: self._rate_type,
            ATTR_CURRENCY: self._currency,
            ATTR_SIDE: self._side,
            ATTR_API_DATE: data.api_date,
        }
