"""Repair notices of the coordinator: a certificate problem is reported at
once, other transport failures after three refreshes in a row, and the
notice disappears with the next successful refresh."""
from __future__ import annotations

from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sed_earthquakes.const import (
    CONF_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MIN_MAGNITUDE,
    CONF_RADIUS_KM,
    DOMAIN,
)
from custom_components.sed_earthquakes.coordinator import SedEarthquakesCoordinator

DATA = {CONF_LATITUDE: 46.948, CONF_LONGITUDE: 7.447, CONF_RADIUS_KM: 150.0, CONF_MIN_MAGNITUDE: 1.0, CONF_DAYS: 30}


@pytest.fixture
def entry(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="46.95_7.45_150.0", title="SED", data=DATA)
    entry.add_to_hass(hass)
    return entry


def _issue(hass: HomeAssistant, entry):
    return ir.async_get(hass).async_get_issue(DOMAIN, f"unreachable_{entry.entry_id}")


async def test_unreachable_notice_after_three_failures_and_recovery(hass: HomeAssistant, enable_custom_integrations, entry) -> None:
    coordinator = SedEarthquakesCoordinator(hass, entry)
    with patch("custom_components.sed_earthquakes.coordinator.async_fetch_quakes", side_effect=TimeoutError()):
        for n in range(3):
            await coordinator.async_refresh()
            assert coordinator.last_update_success is False
            assert (_issue(hass, entry) is not None) is (n == 2), f"after failure {n + 1}"
    issue = _issue(hass, entry)
    assert issue.translation_key == "unreachable"
    assert issue.translation_placeholders["error"] == "timeout"

    with patch("custom_components.sed_earthquakes.coordinator.async_fetch_quakes", return_value={}):
        await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert coordinator.data == {"quakes": {}, "count": 0}
    assert _issue(hass, entry) is None


async def test_certificate_problem_is_reported_at_once(hass: HomeAssistant, enable_custom_integrations, entry) -> None:
    coordinator = SedEarthquakesCoordinator(hass, entry)
    err = aiohttp.ClientSSLError(None, OSError("certificate verify failed"))
    with patch("custom_components.sed_earthquakes.coordinator.async_fetch_quakes", side_effect=err):
        await coordinator.async_refresh()
    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.translation_key == "certificate"
