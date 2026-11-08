"""Config flow for the Swiss Earthquakes (SED) integration.

Setup: location + radius + minimum magnitude + time window. Reconfigure
(the entry's menu under Settings → Devices & services) changes the same
values in place: the entry keeps its id, so its entities keep their ids
and history; the device name, the entry title and the map follow the new
values after the reload.
"""
from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult

from .const import (
    CONF_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MIN_MAGNITUDE,
    CONF_RADIUS_KM,
    DEFAULT_DAYS,
    DEFAULT_MIN_MAGNITUDE,
    DEFAULT_RADIUS_KM,
    DOMAIN,
)
from .coordinator import async_fetch_quakes, describe_error
from .device import display_radius
from .localization import t

_LOGGER = logging.getLogger(__name__)


def validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Range checks on the submitted values. Keys are form fields, values are
    keys under config.error in strings.json, so each message is shown next to
    its field. Rejecting them here beats creating an entry that only fails on
    its first refresh."""
    errors: dict[str, str] = {}
    if not -90 <= user_input[CONF_LATITUDE] <= 90:
        errors[CONF_LATITUDE] = "invalid_latitude"
    if not -180 <= user_input[CONF_LONGITUDE] <= 180:
        errors[CONF_LONGITUDE] = "invalid_longitude"
    radius = user_input[CONF_RADIUS_KM]
    if not (math.isfinite(radius) and radius > 0):
        errors[CONF_RADIUS_KM] = "invalid_radius"
    if user_input[CONF_DAYS] < 1:
        errors[CONF_DAYS] = "invalid_days"
    return errors


def _unique_id(lat: float, lon: float, radius: float) -> str:
    return f"{round(lat, 2)}_{round(lon, 2)}_{radius}"


def _entry_data(user_input: Mapping[str, Any]) -> dict[str, Any]:
    return {
        CONF_LATITUDE: user_input[CONF_LATITUDE],
        CONF_LONGITUDE: user_input[CONF_LONGITUDE],
        CONF_RADIUS_KM: user_input[CONF_RADIUS_KM],
        CONF_MIN_MAGNITUDE: user_input[CONF_MIN_MAGNITUDE],
        CONF_DAYS: user_input[CONF_DAYS],
    }


def _schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LATITUDE, default=defaults[CONF_LATITUDE]): vol.Coerce(float),
            vol.Required(CONF_LONGITUDE, default=defaults[CONF_LONGITUDE]): vol.Coerce(float),
            vol.Required(CONF_RADIUS_KM, default=defaults[CONF_RADIUS_KM]): vol.Coerce(float),
            vol.Required(CONF_MIN_MAGNITUDE, default=defaults[CONF_MIN_MAGNITUDE]): vol.Coerce(
                float
            ),
            vol.Required(CONF_DAYS, default=defaults[CONF_DAYS]): vol.Coerce(int),
        }
    )


class SedEarthquakesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: location + radius + minimum magnitude + time window."""

    VERSION = 1

    async def _async_validate(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Range checks, then one query with the entered values, so an
        unreachable service shows up in the form instead of as a failed
        setup afterwards."""
        errors = validate_input(user_input)
        if errors:
            return errors
        try:
            await async_fetch_quakes(
                self.hass,
                user_input[CONF_LATITUDE],
                user_input[CONF_LONGITUDE],
                user_input[CONF_RADIUS_KM],
                user_input[CONF_MIN_MAGNITUDE],
                user_input[CONF_DAYS],
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("Connection test to the SED service failed: %s", describe_error(err))
            errors["base"] = "cannot_connect"
        return errors

    def _title(self, user_input: Mapping[str, Any]) -> str:
        return t("device_name", self.hass, radius=display_radius(user_input[CONF_RADIUS_KM]))

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = validate_input(user_input)
            if not errors:
                await self.async_set_unique_id(
                    _unique_id(
                        user_input[CONF_LATITUDE],
                        user_input[CONF_LONGITUDE],
                        user_input[CONF_RADIUS_KM],
                    )
                )
                self._abort_if_unique_id_configured()
                errors = await self._async_validate(user_input)

            if not errors:
                return self.async_create_entry(
                    title=self._title(user_input), data=_entry_data(user_input)
                )

        schema = _schema(
            {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
                CONF_RADIUS_KM: DEFAULT_RADIUS_KM,
                CONF_MIN_MAGNITUDE: DEFAULT_MIN_MAGNITUDE,
                CONF_DAYS: DEFAULT_DAYS,
            }
        )
        if user_input is not None:
            # Show the rejected values again instead of the defaults.
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change location, radius, magnitude or time window of an existing entry.

        The unique id encodes location and radius; a change that would
        collide with another entry is refused, a change that only moves this
        entry updates its unique id. Markers of earthquakes that fall outside
        the new radius or window are removed by the geo_location platform on
        the reload, as they are when an earthquake ages out.
        """
        entry: ConfigEntry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = validate_input(user_input)
            if not errors:
                unique_id = _unique_id(
                    user_input[CONF_LATITUDE],
                    user_input[CONF_LONGITUDE],
                    user_input[CONF_RADIUS_KM],
                )
                await self.async_set_unique_id(unique_id)
                if unique_id != entry.unique_id:
                    self._abort_if_unique_id_configured()
                errors = await self._async_validate(user_input)

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=self._title(user_input),
                    data=_entry_data(user_input),
                    reason="reconfigure_successful",
                )

        schema = _schema(
            {
                CONF_LATITUDE: entry.data.get(CONF_LATITUDE, self.hass.config.latitude),
                CONF_LONGITUDE: entry.data.get(CONF_LONGITUDE, self.hass.config.longitude),
                CONF_RADIUS_KM: entry.data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
                CONF_MIN_MAGNITUDE: entry.data.get(CONF_MIN_MAGNITUDE, DEFAULT_MIN_MAGNITUDE),
                CONF_DAYS: entry.data.get(CONF_DAYS, DEFAULT_DAYS),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)
