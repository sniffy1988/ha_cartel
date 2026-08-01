"""Data update coordinator for HA Cartel."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HaCartelApiError, OfficeRates, async_get_office_rates
from .const import CONF_OFFICE_ID, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HaCartelCoordinator(DataUpdateCoordinator[OfficeRates]):
    """Coordinator that polls Obmenka rates hourly."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
        )
        self.office_id = int(entry.data[CONF_OFFICE_ID])
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> OfficeRates:
        """Fetch rates for the configured office."""
        try:
            return await async_get_office_rates(self.session, self.office_id)
        except HaCartelApiError as err:
            raise UpdateFailed(str(err)) from err
