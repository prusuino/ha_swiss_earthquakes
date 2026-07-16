"""Extra sensors: earthquake count + latest earthquake within the configured radius/time window."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_DAYS, CONF_MIN_MAGNITUDE, CONF_RADIUS_KM, DOMAIN
from .coordinator import SedEarthquakesCoordinator
from .device import device_info
from .localization import magnitude_scale, t

ATTRIBUTION = "Data: Swiss Seismological Service SED, ETH Zurich"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SedEarthquakesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SedEarthquakeCountSensor(hass, coordinator, entry),
            SedLatestEarthquakeSensor(hass, coordinator, entry),
        ]
    )


def _latest(quakes: list[dict]) -> dict | None:
    return max((q for q in quakes if q.get("time")), key=lambda q: q["time"], default=None)


class SedEarthquakeCountSensor(CoordinatorEntity[SedEarthquakesCoordinator], SensorEntity):
    """Number of earthquakes currently recorded within the configured radius/time window."""

    _attr_has_entity_name = False
    _attr_attribution = ATTRIBUTION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:vibrate"

    def __init__(
        self, hass: HomeAssistant, coordinator: SedEarthquakesCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._hass_ref = hass
        self._attr_name = t("count_sensor_name", hass)
        self._attr_unique_id = f"{entry.entry_id}_count"
        self._attr_device_info = device_info(hass, entry)
        radius = entry.data.get(CONF_RADIUS_KM)
        self.entity_id = f"sensor.sed_earthquakes_count_{round(radius)}km"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("count", 0)

    @property
    def extra_state_attributes(self):
        quakes = list((self.coordinator.data or {}).get("quakes", {}).values())
        strongest = max(
            (q for q in quakes if q.get("magnitude") is not None),
            key=lambda q: q["magnitude"],
            default=None,
        )
        return {
            "radius_km": self._entry.data.get(CONF_RADIUS_KM),
            "min_magnitude": self._entry.data.get(CONF_MIN_MAGNITUDE),
            "time_window_days": self._entry.data.get(CONF_DAYS),
            "strongest_quake": strongest,
            "magnitude_scale": magnitude_scale(self._hass_ref),
        }


class SedLatestEarthquakeSensor(CoordinatorEntity[SedEarthquakesCoordinator], SensorEntity):
    """Time of the most recent earthquake within the configured radius.

    State = timestamp (device_class timestamp) so automations can reliably
    trigger on a new event — even if a new quake happens to have the same
    magnitude as the previous one. Details as attributes.
    """

    _attr_has_entity_name = False
    _attr_attribution = ATTRIBUTION
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-alert-outline"

    def __init__(
        self, hass: HomeAssistant, coordinator: SedEarthquakesCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = t("latest_sensor_name", hass)
        self._attr_unique_id = f"{entry.entry_id}_latest"
        self._attr_device_info = device_info(hass, entry)
        radius = entry.data.get(CONF_RADIUS_KM)
        self.entity_id = f"sensor.sed_earthquakes_latest_{round(radius)}km"

    def _quake(self) -> dict | None:
        quakes = list((self.coordinator.data or {}).get("quakes", {}).values())
        return _latest(quakes)

    @property
    def native_value(self):
        q = self._quake()
        if not q or not q.get("time"):
            return None
        parsed = dt_util.parse_datetime(q["time"])
        if parsed is None:
            return None
        return dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)

    @property
    def extra_state_attributes(self):
        q = self._quake()
        if not q:
            return {}
        return {
            "magnitude": q.get("magnitude"),
            "magnitude_type": q.get("magnitude_type"),
            "depth_km": q.get("depth_km"),
            "place": q.get("place"),
            "distance_km": q.get("distance_km"),
            "event_id": q.get("event_id"),
        }
