"""DataUpdateCoordinator for earthquake data from the Swiss Seismological Service (SED).

Uses the official, internationally standardized FDSN Event Web Service
(fdsnws-event) provided by the SED — no external library, plain aiohttp
plus text parsing.
"""
from __future__ import annotations

import logging
import math
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MIN_MAGNITUDE,
    CONF_RADIUS_KM,
    DOMAIN,
    FDSN_URL,
    KM_PER_DEGREE,
    UPDATE_INTERVAL_MINUTES,
)
from .localization import t

_LOGGER = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_fdsn_text(text: str, lat: float, lon: float, hass: HomeAssistant) -> dict[str, dict]:
    """Parse the FDSN 'text' format (pipe-separated, header starts with '#')."""
    quakes: dict[str, dict] = {}
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if len(lines) <= 1:
        return quakes

    header = [h.lstrip("#").strip() for h in lines[0].split("|")]
    for line in lines[1:]:
        cols = line.split("|")
        if len(cols) != len(header):
            continue
        row = dict(zip(header, cols))
        try:
            lat_e = float(row["Latitude"])
            lon_e = float(row["Longitude"])
        except (KeyError, ValueError):
            continue

        event_id = row.get("EventID") or row.get("#EventID")
        if not event_id:
            continue

        magnitude = None
        if row.get("Magnitude"):
            try:
                magnitude = round(float(row["Magnitude"]), 2)
            except ValueError:
                pass

        depth_km = None
        if row.get("Depth/km"):
            try:
                depth_km = round(float(row["Depth/km"]), 1)
            except ValueError:
                pass

        quakes[event_id] = {
            "event_id": event_id,
            "time": row.get("Time"),
            "latitude": lat_e,
            "longitude": lon_e,
            "depth_km": depth_km,
            "magnitude": magnitude,
            "magnitude_type": row.get("MagType"),
            "place": row.get("EventLocationName") or t("unknown_place", hass),
            "distance_km": round(_haversine_km(lat, lon, lat_e, lon_e), 1),
        }
    return quakes


async def async_fetch_quakes(
    hass: HomeAssistant, lat: float, lon: float, radius_km: float, min_magnitude: float, days: int
) -> dict[str, dict]:
    session = async_get_clientsession(hass)
    starttime = (dt_util.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "format": "text",
        "latitude": lat,
        "longitude": lon,
        "maxradius": radius_km / KM_PER_DEGREE,
        "minmagnitude": min_magnitude,
        "starttime": starttime,
        "eventtype": "earthquake",
        "orderby": "time",
        "limit": 200,
    }
    async with session.get(FDSN_URL, params=params, timeout=25) as resp:
        resp.raise_for_status()
        text = await resp.text()
    return _parse_fdsn_text(text, lat, lon, hass)


class SedEarthquakesCoordinator(DataUpdateCoordinator[dict]):
    """Fetches current earthquakes within the configured radius/time window."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self._entry = entry

    async def _async_update_data(self) -> dict:
        data = self._entry.data
        try:
            quakes = await async_fetch_quakes(
                self.hass,
                data[CONF_LATITUDE],
                data[CONF_LONGITUDE],
                data[CONF_RADIUS_KM],
                data[CONF_MIN_MAGNITUDE],
                data[CONF_DAYS],
            )
        except Exception as err:
            raise UpdateFailed(f"SED earthquake data unreachable: {err}") from err
        return {"quakes": quakes, "count": len(quakes)}
