"""Geo-location entities for current earthquakes — appear automatically on the
Home Assistant map card.

Custom lightweight management instead of an external feed-manager package: on
every coordinator update, the current earthquake list is diffed against the
entities already created (new ones added, ones that fell out of the window
removed, known ones refreshed).
"""
from __future__ import annotations

import logging

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SedEarthquakesCoordinator
from .localization import t

_LOGGER = logging.getLogger(__name__)
SOURCE = "sed_earthquakes"
ATTRIBUTION = "Data: Swiss Seismological Service SED, ETH Zurich"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SedEarthquakesCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_entities: dict[str, SedEarthquakeEvent] = {}

    @callback
    def _sync_entities() -> None:
        quakes = (coordinator.data or {}).get("quakes", {})

        new_entities: list[SedEarthquakeEvent] = []
        for event_id, quake in quakes.items():
            entity = known_entities.get(event_id)
            if entity is None:
                entity = SedEarthquakeEvent(hass, quake)
                known_entities[event_id] = entity
                new_entities.append(entity)
            else:
                # The SED revises location, depth and magnitude after manual
                # review, so a known event must follow those corrections
                # instead of staying on the values it was first published with.
                entity.async_apply_revision(quake)
        if new_entities:
            async_add_entities(new_entities)

        for event_id in [e for e in known_entities if e not in quakes]:
            entity = known_entities.pop(event_id)
            hass.async_create_task(entity.async_remove(force_remove=True))

    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))
    _sync_entities()


def _icon_for_magnitude(magnitude: float | None) -> str:
    if magnitude is None:
        return "mdi:pulse"
    if magnitude >= 4:
        return "mdi:alert-octagon"
    if magnitude >= 2.5:
        return "mdi:alert"
    return "mdi:circle-small"


class SedEarthquakeEvent(GeolocationEvent):
    """A single earthquake event. The lifecycle (appearing, being revised,
    disappearing) is managed by the sync function above."""

    _attr_should_poll = False
    _attr_source = SOURCE
    _attr_attribution = ATTRIBUTION
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_has_entity_name = False
    # Hidden from Home Assistant's auto-generated default dashboard map (which
    # otherwise draws every geo_location entity in the system) — still shown
    # on a map card that references them by source, which does not go through
    # the visible-by-default list. This applies to entities registered for the
    # first time; whether an existing entity stays hidden is the user's
    # decision alone and is never rewritten from here.
    _attr_entity_registry_visible_default = False

    def __init__(self, hass: HomeAssistant, quake: dict) -> None:
        self._hass = hass
        self._attr_unique_id = f"{DOMAIN}_{quake['event_id']}"
        self._apply(quake)

    def _apply(self, quake: dict) -> None:
        """Take over the values of an earthquake record."""
        self._quake = quake
        magnitude = quake.get("magnitude")
        mag_text = f"M{magnitude}" if magnitude is not None else "M?"
        prefix = t("quake_entity_prefix", self._hass)
        self._attr_name = f"{prefix} {mag_text} – {quake.get('place')}"
        self._attr_latitude = quake["latitude"]
        self._attr_longitude = quake["longitude"]
        self._attr_distance = quake["distance_km"]
        self._attr_icon = _icon_for_magnitude(magnitude)

    @callback
    def async_apply_revision(self, quake: dict) -> None:
        """Follow a revised version of this event.

        The unique_id is derived from the event ID and stays the same, so the
        entity_id is unaffected — only the displayed name, the marker position
        and the attributes follow the revision.
        """
        if quake == self._quake:
            return
        self._apply(quake)
        if self.hass is not None and self.entity_id:
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {
            "magnitude": self._quake.get("magnitude"),
            "magnitude_type": self._quake.get("magnitude_type"),
            "depth_km": self._quake.get("depth_km"),
            "time": self._quake.get("time"),
            "place": self._quake.get("place"),
        }
