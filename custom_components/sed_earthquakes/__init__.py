"""Swiss Earthquakes (SED) integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import SedEarthquakesCoordinator

type SedEarthquakesConfigEntry = ConfigEntry[SedEarthquakesCoordinator]
from .frontend import async_serve_frontend

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "geo_location"]


async def async_setup_entry(hass: HomeAssistant, entry: SedEarthquakesConfigEntry) -> bool:
    try:
        await async_serve_frontend(hass)
    except Exception:  # noqa: BLE001 - serving the strategy file must never block integration setup
        _LOGGER.exception("Serving the bundled dashboard strategy failed")

    coordinator = SedEarthquakesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SedEarthquakesConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # A notice about the service belongs to the entry that polls it.
        ir.async_delete_issue(hass, DOMAIN, f"unreachable_{entry.entry_id}")
    return unloaded
