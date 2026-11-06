"""Triggers for Swiss Earthquakes (SED).

"Earthquake detected" for the automation editor's trigger list, with an
optional minimum magnitude. It watches the integration's latest-earthquake
entity (a timestamp, so two quakes of the same size at the same place are
still told apart) and reads the magnitude from its attributes. A target
that expands to other entities (a device, an area) is narrowed to the ones
this integration created.

The trigger platform API arrived in Home Assistant 2026.10. On an older
version the module still imports, but offers no triggers.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import CONF_FOR, CONF_OPTIONS, CONF_TARGET
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import DOMAIN

CONF_MINIMUM_MAGNITUDE = "minimum_magnitude"

try:
    from homeassistant.helpers.automation import DomainSpec
    from homeassistant.helpers.trigger import (
        ATTR_BEHAVIOR,
        BEHAVIOR_ALL,
        BEHAVIOR_EACH,
        BEHAVIOR_FIRST,
        EntityTriggerBase,
        Trigger,
    )
except ImportError:  # Home Assistant before 2026.10: no trigger platform API
    TRIGGERS: dict = {}
else:
    LATEST_DOMAIN_SPECS = {SENSOR_DOMAIN: DomainSpec(device_class=SensorDeviceClass.TIMESTAMP)}

    # The core's entity-state schema (target + behavior + for) plus the
    # magnitude option, spelled out because the nested options mapping
    # cannot be extended in place.
    EARTHQUAKE_SCHEMA = vol.Schema(
        {
            vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
            vol.Required(CONF_OPTIONS, default={}): {
                vol.Required(ATTR_BEHAVIOR, default=BEHAVIOR_EACH): vol.In(
                    [BEHAVIOR_FIRST, BEHAVIOR_ALL, BEHAVIOR_EACH]
                ),
                vol.Optional(CONF_FOR): cv.positive_time_period,
                vol.Optional(CONF_MINIMUM_MAGNITUDE, default=0.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=10)
                ),
            },
        }
    )

    def _own_entities(hass: HomeAssistant, entities: set[str]) -> set[str]:
        """Keep only entities created by this integration."""
        registry = er.async_get(hass)
        return {
            entity_id
            for entity_id in entities
            if (entry := registry.async_get(entity_id)) is not None
            and entry.platform == DOMAIN
        }

    class _EarthquakeDetected(EntityTriggerBase):
        """The latest-earthquake entity changes: a new earthquake was recorded.

        Fires on every new event by default; with a minimum magnitude only
        when the new event is at least that strong."""

        _domain_specs = LATEST_DOMAIN_SPECS
        _schema = EARTHQUAKE_SCHEMA

        def __init__(self, hass: HomeAssistant, config) -> None:
            super().__init__(hass, config)
            self._minimum = float(self._options.get(CONF_MINIMUM_MAGNITUDE) or 0.0)

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

        def is_valid_state(self, state: State, report_not_triggered) -> bool:
            if self._minimum <= 0:
                return True
            magnitude = state.attributes.get("magnitude")
            if magnitude is None:
                # The SED has not rated the event yet: it cannot pass a
                # magnitude threshold, say so in the trace.
                report_not_triggered("magnitude_unknown", entity_id=state.entity_id)
                return False
            return float(magnitude) >= self._minimum

    TRIGGERS: dict[str, type[Trigger]] = {"earthquake_detected": _EarthquakeDetected}


async def async_get_triggers(hass: HomeAssistant) -> dict:
    """Return the triggers of this integration."""
    return TRIGGERS
