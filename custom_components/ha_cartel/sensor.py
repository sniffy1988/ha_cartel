"""Sensor platform for HA Cartel."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CurrencyRate, OfficeRates
from .const import (
    ATTR_API_DATE,
    ATTR_CITY,
    ATTR_CURRENCY,
    ATTR_CURRENCY_NAME,
    ATTR_OFFICE_ID,
    ATTR_OPT,
    ATTR_SIDE,
    ATTR_TO_CURRENCY,
    ATTR_TO_CURRENCY_NAME,
    CURRENCY_ICONS,
    DOMAIN,
    currency_name,
)
from .coordinator import HaCartelCoordinator

SIDE_BUY = "buy"
SIDE_SELL = "sell"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HA Cartel buy/sell sensors from a config entry."""
    coordinator: HaCartelCoordinator = entry.runtime_data
    entities: list[HaCartelRateSensor] = []

    for rate in coordinator.data.currencies:
        if rate.buy is not None:
            entities.append(
                HaCartelRateSensor(
                    coordinator, rate, SIDE_BUY, opt=False, value_fn=lambda r: r.buy
                )
            )
        if rate.sell is not None:
            entities.append(
                HaCartelRateSensor(
                    coordinator, rate, SIDE_SELL, opt=False, value_fn=lambda r: r.sell
                )
            )
        if rate.buy_opt is not None:
            entities.append(
                HaCartelRateSensor(
                    coordinator,
                    rate,
                    SIDE_BUY,
                    opt=True,
                    value_fn=lambda r: r.buy_opt,
                )
            )
        if rate.sell_opt is not None:
            entities.append(
                HaCartelRateSensor(
                    coordinator,
                    rate,
                    SIDE_SELL,
                    opt=True,
                    value_fn=lambda r: r.sell_opt,
                )
            )

    async_add_entities(entities)


class HaCartelRateSensor(CoordinatorEntity[HaCartelCoordinator], SensorEntity):
    """Buy or sell rate for one currency or cross pair."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: HaCartelCoordinator,
        rate: CurrencyRate,
        side: str,
        *,
        opt: bool,
        value_fn: Callable[[CurrencyRate], float | None],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._currency = rate.currency
        self._to_currency = rate.to_currency
        self._side = side
        self._opt = opt
        self._value_fn = value_fn
        office_id = coordinator.office_id
        suffix = f"{side}_opt" if opt else side
        self._attr_unique_id = f"{DOMAIN}_{office_id}_{rate.key}_{suffix}"
        side_label = "Buy" if side == SIDE_BUY else "Sell"
        name = f"{rate.label} {side_label}"
        if opt:
            name = f"{name} Opt"
        self._attr_name = name
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
        """Return this sensor's rate."""
        rate = self._current_rate()
        if rate is None:
            return None
        return self._value_fn(rate)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool | None]:
        """Return extra attributes."""
        data = self.coordinator.data
        return {
            ATTR_CITY: data.city,
            ATTR_OFFICE_ID: data.office_id,
            ATTR_CURRENCY: self._currency,
            ATTR_CURRENCY_NAME: currency_name(self._currency),
            ATTR_TO_CURRENCY: self._to_currency,
            ATTR_TO_CURRENCY_NAME: currency_name(self._to_currency),
            ATTR_SIDE: self._side,
            ATTR_OPT: self._opt,
            ATTR_API_DATE: data.api_date,
        }
