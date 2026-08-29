"""Config flow for the Swiss Earthquakes (SED) integration."""
from __future__ import annotations

import logging
import math
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

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


class SedEarthquakesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: location + radius + minimum magnitude + time window."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            lat = user_input[CONF_LATITUDE]
            lon = user_input[CONF_LONGITUDE]
            radius = user_input[CONF_RADIUS_KM]
            errors = validate_input(user_input)
            if not errors:
                unique_id = f"{round(lat, 2)}_{round(lon, 2)}_{radius}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # One query with the entered values, so an unreachable service
                # shows up in the form instead of as a failed setup afterwards.
                try:
                    await async_fetch_quakes(
                        self.hass,
                        lat,
                        lon,
                        radius,
                        user_input[CONF_MIN_MAGNITUDE],
                        user_input[CONF_DAYS],
                    )
                except (aiohttp.ClientError, TimeoutError) as err:
                    _LOGGER.warning(
                        "Connection test to the SED service failed: %s", describe_error(err)
                    )
                    errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=t("device_name", self.hass, radius=display_radius(radius)),
                    data={
                        CONF_LATITUDE: lat,
                        CONF_LONGITUDE: lon,
                        CONF_RADIUS_KM: radius,
                        CONF_MIN_MAGNITUDE: user_input[CONF_MIN_MAGNITUDE],
                        CONF_DAYS: user_input[CONF_DAYS],
                    },
                )

        default_lat = self.hass.config.latitude
        default_lon = self.hass.config.longitude

        schema = vol.Schema(
            {
                vol.Required(CONF_LATITUDE, default=default_lat): vol.Coerce(float),
                vol.Required(CONF_LONGITUDE, default=default_lon): vol.Coerce(float),
                vol.Required(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): vol.Coerce(float),
                vol.Required(CONF_MIN_MAGNITUDE, default=DEFAULT_MIN_MAGNITUDE): vol.Coerce(float),
                vol.Required(CONF_DAYS, default=DEFAULT_DAYS): vol.Coerce(int),
            }
        )
        if user_input is not None:
            # Show the rejected values again instead of the defaults.
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
