"""Config flow for HA Cartel."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig

from .api import HaCartelApiError, OfficeInfo, async_get_offices
from .const import CONF_CITY, CONF_OFFICE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HaCartelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Cartel."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._offices: list[OfficeInfo] = []
        self._city: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial city selection step."""
        errors: dict[str, str] = {}

        if not self._offices:
            try:
                session = async_get_clientsession(self.hass)
                self._offices = await async_get_offices(session)
            except HaCartelApiError:
                _LOGGER.exception("Failed to fetch offices")
                return self.async_abort(reason="cannot_connect")
            except Exception:
                _LOGGER.exception("Unexpected error fetching offices")
                return self.async_abort(reason="cannot_connect")

        if not self._offices:
            return self.async_abort(reason="no_offices")

        cities = sorted({office.city for office in self._offices})

        if user_input is not None:
            self._city = user_input[CONF_CITY]
            return await self.async_step_office()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=city, label=city)
                                for city in cities
                            ],
                            mode="dropdown",
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_office(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle office selection for the chosen city."""
        assert self._city is not None

        city_offices = [
            office for office in self._offices if office.city == self._city
        ]
        if not city_offices:
            return self.async_abort(reason="no_offices")

        if user_input is not None:
            office_id = int(user_input[CONF_OFFICE_ID])
            await self.async_set_unique_id(str(office_id))
            self._abort_if_unique_id_configured()

            office = next(
                (item for item in city_offices if item.office_id == office_id),
                None,
            )
            title_city = office.city if office else self._city
            return self.async_create_entry(
                title=f"{title_city} ({office_id})",
                data={
                    CONF_CITY: title_city,
                    CONF_OFFICE_ID: office_id,
                },
            )

        options: list[SelectOptionDict] = []
        for office in sorted(city_offices, key=lambda item: item.office_id):
            label = f"Office {office.office_id}"
            if office.is_first:
                label = f"{label} (primary)"
            options.append(
                SelectOptionDict(value=str(office.office_id), label=label)
            )

        return self.async_show_form(
            step_id="office",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OFFICE_ID): SelectSelector(
                        SelectSelectorConfig(options=options, mode="dropdown")
                    )
                }
            ),
            description_placeholders={"city": self._city},
        )
