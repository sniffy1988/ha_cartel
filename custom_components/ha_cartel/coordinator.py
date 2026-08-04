"""Data update coordinator for HA Cartel."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HaCartelApiError, OfficeRates, async_get_office_rates
from .const import CONF_OFFICE_ID, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Retry sooner after a failed poll so sensors do not stay unavailable for an hour.
RETRY_INTERVAL = timedelta(minutes=5)


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
            data = await async_get_office_rates(self.session, self.office_id)
        except HaCartelApiError as err:
            self.update_interval = RETRY_INTERVAL
            _LOGGER.warning(
                "HA Cartel office %s update failed (next try in %s): %s",
                self.office_id,
                RETRY_INTERVAL,
                err,
            )
            raise UpdateFailed(str(err)) from err

        self.update_interval = UPDATE_INTERVAL
        return data
