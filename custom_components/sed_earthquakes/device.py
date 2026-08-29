"""Shared device info and entity-id helpers for all platforms."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import CONF_RADIUS_KM, DOMAIN
from .localization import t


def entry_suffix(entry: ConfigEntry) -> str:
    """Short per-entry discriminator for suggested entity ids: the last four
    characters of the config entry id, lower-cased (entry ids are ULIDs, so
    the tail is random and stays fixed for the life of the entry).

    The radius alone does not tell two entries apart: the config flow allows
    a second entry at another location with the same radius (a home and a
    holiday location, say), and its sensors would then suggest the very same
    object ids, which Home Assistant resolves by appending _2 to whichever
    entry loads second — an automation copied between the entries silently
    targets the wrong one. The suffix keeps them apart. It only affects the
    id suggested on first creation; unique ids are untouched and existing
    entities keep the ids they have."""
    return entry.entry_id[-4:].lower()


def display_radius(radius: float | int | None) -> str:
    """The radius as shown in names, without a trailing .0: the config flow
    stores it as a float, so 150 would otherwise read "150.0 km" in the
    device name while the entity ids say 150km."""
    try:
        value = float(radius)
    except (TypeError, ValueError):
        return str(radius)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def device_info(hass: HomeAssistant, entry: ConfigEntry) -> DeviceInfo:
    radius = entry.data.get(CONF_RADIUS_KM)
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=t("device_name", hass, radius=display_radius(radius)),
        manufacturer=t("manufacturer", hass),
        model=t("model", hass),
        entry_type=DeviceEntryType.SERVICE,
    )
