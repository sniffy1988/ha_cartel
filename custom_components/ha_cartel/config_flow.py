"""Config flow for HA Cartel."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HaCartelApiError, async_get_office_rates
from .const import (
    CONF_CITY,
    CONF_OFFICE_ID,
    DEFAULT_CITY,
    DEFAULT_OFFICE_ID,
    DOMAIN,
    INTEGRATION_TITLE,
)

_LOGGER = logging.getLogger(__name__)


class HaCartelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Cartel (Kharkiv #1 only)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm and add the fixed Kharkiv office."""
        if user_input is not None:
            return await self._async_create_entry()

        try:
            session = async_get_clientsession(self.hass)
            await async_get_office_rates(session, DEFAULT_OFFICE_ID)
        except HaCartelApiError:
            _LOGGER.exception("Failed to fetch Kharkiv office rates")
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Unexpected error fetching Kharkiv office rates")
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "office": INTEGRATION_TITLE,
            },
        )

    async def _async_create_entry(self) -> ConfigFlowResult:
        """Create the single allowed config entry."""
        await self.async_set_unique_id(str(DEFAULT_OFFICE_ID))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=INTEGRATION_TITLE,
            data={
                CONF_CITY: DEFAULT_CITY,
                CONF_OFFICE_ID: DEFAULT_OFFICE_ID,
            },
        )
