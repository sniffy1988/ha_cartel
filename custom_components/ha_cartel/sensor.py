"""Sensor platform for HA Cartel."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CurrencyRate, OfficeRates
from .const import (
    ATTR_API_DATE,
    ATTR_BUY,
    ATTR_BUY_OPT,
    ATTR_CITY,
    ATTR_CURRENCY,
    ATTR_CURRENCY_NAME,
    ATTR_OFFICE_ID,
    ATTR_SELL,
    ATTR_SELL_OPT,
    ATTR_TO_CURRENCY,
    ATTR_TO_CURRENCY_NAME,
    CURRENCY_ICONS,
    DOMAIN,
    currency_name,
)
from .coordinator import HaCartelCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HA Cartel sensors from a config entry."""
    coordinator: HaCartelCoordinator = entry.runtime_data
    async_add_entities(
        HaCartelCurrencySensor(coordinator, rate)
        for rate in coordinator.data.currencies
    )


class HaCartelCurrencySensor(CoordinatorEntity[HaCartelCoordinator], SensorEntity):
    """One sensor per currency/pair with buy, sell, and opt attributes."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: HaCartelCoordinator,
        rate: CurrencyRate,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._currency = rate.currency
        self._to_currency = rate.to_currency
        office_id = coordinator.office_id
        self._attr_unique_id = f"{DOMAIN}_{office_id}_{rate.key}"
        self._attr_name = rate.label
        self._attr_native_unit_of_measurement = rate.to_currency or "UAH"
        self._attr_icon = CURRENCY_ICONS.get(
            rate.to_currency or rate.currency, "mdi:currency-usd"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(office_id))},
            name=f"Obmenka {coordinator.data.city} ({office_id})",
            manufacturer="Obmenka",
            model="Exchange rates",
            configuration_url="https://obmenka.dn.ua",
        )

    def _current_rate(self) -> CurrencyRate | None:
        """Find this currency in the latest coordinator data."""
        data: OfficeRates = self.coordinator.data
        for rate in data.currencies:
            if (
                rate.currency == self._currency
                and rate.to_currency == self._to_currency
            ):
                return rate
        return None

    @property
    def native_value(self) -> float | None:
        """Return primary rate (cash buy, else opt buy, else sell)."""
        rate = self._current_rate()
        return None if rate is None else rate.primary

    @property
    def extra_state_attributes(self) -> dict[str, str | int | float | None]:
        """Expose buy/sell and opt values on one sensor."""
        data = self.coordinator.data
        rate = self._current_rate()
        attrs: dict[str, str | int | float | None] = {
            ATTR_CITY: data.city,
            ATTR_OFFICE_ID: data.office_id,
            ATTR_CURRENCY: self._currency,
            ATTR_CURRENCY_NAME: currency_name(self._currency),
            ATTR_TO_CURRENCY: self._to_currency,
            ATTR_TO_CURRENCY_NAME: currency_name(self._to_currency),
            ATTR_API_DATE: data.api_date,
        }
        if rate is not None:
            attrs[ATTR_BUY] = rate.buy
            attrs[ATTR_SELL] = rate.sell
            if rate.buy_opt is not None or rate.sell_opt is not None:
                attrs[ATTR_BUY_OPT] = rate.buy_opt
                attrs[ATTR_SELL_OPT] = rate.sell_opt
        return attrs
