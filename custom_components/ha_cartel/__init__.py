"""The HA Cartel integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import HaCartelCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type HaCartelConfigEntry = ConfigEntry[HaCartelCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HaCartelConfigEntry) -> bool:
    """Set up HA Cartel from a config entry."""
    coordinator = HaCartelCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaCartelConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
