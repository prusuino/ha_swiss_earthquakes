"""Conditions for Swiss Earthquakes (SED).

"Recent earthquake" for the automation editor's condition list: the
latest-earthquake sensor of a location holds the time of the newest event
and its magnitude as an attribute, so an automation can ask whether an
earthquake of at least a given magnitude happened within the last hours.
As with the trigger, a target that expands to other entities is narrowed to
the sensors this integration created.

The condition platform API arrived in Home Assistant 2026.11. On an older
version the module still imports, but offers no conditions.
"""
from __future__ import annotations

from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import CONF_FOR, CONF_OPTIONS, CONF_TARGET
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN

CONF_HOURS = "hours"
CONF_MINIMUM_MAGNITUDE = "minimum_magnitude"

try:
    from homeassistant.helpers.automation import DomainSpec
    from homeassistant.helpers.condition import (
        ATTR_BEHAVIOR,
        BEHAVIOR_ALL,
        BEHAVIOR_ANY,
        Condition,
        EntityConditionBase,
    )
except ImportError:  # Home Assistant before 2026.11: no condition platform API
    CONDITIONS: dict = {}
else:
    LATEST_DOMAIN_SPECS = {SENSOR_DOMAIN: DomainSpec(device_class=SensorDeviceClass.TIMESTAMP)}

    RECENT_SCHEMA = vol.Schema(
        {
            vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
            vol.Required(CONF_OPTIONS, default={}): {
                vol.Required(ATTR_BEHAVIOR, default=BEHAVIOR_ANY): vol.In([BEHAVIOR_ANY, BEHAVIOR_ALL]),
                vol.Optional(CONF_FOR): cv.positive_time_period,
                vol.Optional(CONF_HOURS, default=24): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=720)),
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

    class _RecentEarthquake(EntityConditionBase):
        """The newest earthquake of a location is at most N hours old and at
        least as strong as the minimum magnitude."""

        _domain_specs = LATEST_DOMAIN_SPECS
        _schema = RECENT_SCHEMA

        def __init__(self, hass: HomeAssistant, config) -> None:
            super().__init__(hass, config)
            options = config.options or {}
            self._window = timedelta(hours=float(options.get(CONF_HOURS) or 24))
            self._minimum = float(options.get(CONF_MINIMUM_MAGNITUDE) or 0.0)

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

        def is_valid_state(self, entity_state: State) -> bool:
            when = dt_util.parse_datetime(entity_state.state)
            if when is None:
                return False
            if dt_util.utcnow() - dt_util.as_utc(when) > self._window:
                return False
            if self._minimum <= 0:
                return True
            magnitude = entity_state.attributes.get("magnitude")
            try:
                return magnitude is not None and float(magnitude) >= self._minimum
            except (TypeError, ValueError):
                return False

    CONDITIONS: dict[str, type[Condition]] = {"recent_earthquake": _RecentEarthquake}


async def async_get_conditions(hass: HomeAssistant) -> dict:
    """Return the conditions of this integration."""
    return CONDITIONS
