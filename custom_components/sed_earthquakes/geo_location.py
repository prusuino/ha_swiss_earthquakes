"""Geo-location entities for current earthquakes — appear automatically on the
Home Assistant map card.

Custom lightweight management instead of an external feed-manager package: on
every coordinator update, the current earthquake list is diffed against the
entities already created (new ones added, ones that fell out of the window
removed, known ones refreshed in place so their marker follows revisions and
the coordinator's availability).
"""
from __future__ import annotations

import logging

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SedEarthquakesCoordinator
from .localization import t

_LOGGER = logging.getLogger(__name__)
SOURCE = "sed_earthquakes"
ATTRIBUTION = "Data: Swiss Seismological Service SED, ETH Zurich"

_UNIQUE_ID_PREFIX = f"{DOMAIN}_"


def _entry_unique_id_prefix(entry_id: str) -> str:
    """Unique-id prefix of one config entry's markers. The entry id is part of
    it so two entries whose areas overlap (a home and a holiday location a few
    hundred kilometres apart, say) each get their own marker for a shared
    earthquake instead of fighting over one registry entry — Home Assistant
    refuses the second as a duplicate id and the quake silently goes missing
    from that entry's map."""
    return f"{_UNIQUE_ID_PREFIX}{entry_id}_"


def _migrate_marker_registry(registry: er.EntityRegistry, entry_id: str) -> None:
    """One-time registry maintenance for this entry's map markers, run before
    the first marker is added so nothing gets registered twice.

    Markers used to be keyed by the SED event id alone (see
    _entry_unique_id_prefix). Those are migrated in place to the entry-scoped
    id, so the entity id, its history and whatever the user changed on it
    (name, visibility, area) survive. Already migrated entries are left
    untouched, which makes the routine safe to run on every setup.

    Only registry entries belonging to this config entry are touched.
    """
    entry_prefix = _entry_unique_id_prefix(entry_id)
    for reg_entry in er.async_entries_for_config_entry(registry, entry_id):
        if reg_entry.domain != "geo_location":
            continue
        unique_id = reg_entry.unique_id
        if unique_id.startswith(entry_prefix) or not unique_id.startswith(_UNIQUE_ID_PREFIX):
            continue
        new_unique_id = f"{entry_prefix}{unique_id[len(_UNIQUE_ID_PREFIX):]}"
        if registry.async_get_entity_id("geo_location", DOMAIN, new_unique_id):
            # The migrated twin already exists (a downgrade to an earlier
            # release registered the old id again next to it) — this one
            # would only be a duplicate now.
            registry.async_remove(reg_entry.entity_id)
            continue
        registry.async_update_entity(reg_entry.entity_id, new_unique_id=new_unique_id)
        _LOGGER.debug("Migrated map marker %s to the entry-scoped unique id", reg_entry.entity_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SedEarthquakesCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_entities: dict[str, SedEarthquakeEvent] = {}

    # Before the first marker is added, so nothing gets registered twice.
    _migrate_marker_registry(er.async_get(hass), entry.entry_id)

    @callback
    def _sync_entities() -> None:
        # Runs on every coordinator notification — including a failed
        # refresh, which keeps the previous data but flips
        # last_update_success. The in-place update below then writes state
        # for every surviving marker, which is what publishes the
        # availability change (see SedEarthquakeEvent.available).
        quakes = (coordinator.data or {}).get("quakes", {})

        new_entities: list[SedEarthquakeEvent] = []
        for event_id, quake in quakes.items():
            entity = known_entities.get(event_id)
            if entity is None:
                entity = SedEarthquakeEvent(hass, coordinator, entry.entry_id, quake)
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
    disappearing) is managed by the sync function above; availability follows
    the coordinator's last refresh."""

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

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SedEarthquakesCoordinator,
        entry_id: str,
        quake: dict,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._attr_unique_id = f"{_entry_unique_id_prefix(entry_id)}{quake['event_id']}"
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
        """Follow a revised version of this event and republish the state.

        The unique_id is derived from the event ID and stays the same, so the
        entity_id is unaffected — only the displayed name, the marker position
        and the attributes follow the revision. State is written even when the
        record is unchanged: after a failed refresh the data is the same but
        the availability is not, and that flip has to reach the state machine.
        """
        if quake != self._quake:
            self._apply(quake)
        if self.hass is not None and self.entity_id:
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Like the sensors: while the SED service is unreachable the marker is
        unavailable instead of showing its last known label indefinitely.
        Not a CoordinatorEntity (the lifecycle is managed by the sync
        function), so this reads the coordinator directly; the sync function
        writes state after every refresh, failed ones included, so a flip
        reaches the state machine."""
        return self._coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        return {
            "magnitude": self._quake.get("magnitude"),
            "magnitude_type": self._quake.get("magnitude_type"),
            "depth_km": self._quake.get("depth_km"),
            "time": self._quake.get("time"),
            "place": self._quake.get("place"),
        }
