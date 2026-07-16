"""Config flow for the Swiss Earthquakes (SED) integration."""
from __future__ import annotations

from typing import Any

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
from .localization import t


class SedEarthquakesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: location + radius + minimum magnitude + time window."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            lat = user_input[CONF_LATITUDE]
            lon = user_input[CONF_LONGITUDE]
            radius = user_input[CONF_RADIUS_KM]
            unique_id = f"{round(lat, 2)}_{round(lon, 2)}_{radius}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=t("device_name", self.hass, radius=radius),
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
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
