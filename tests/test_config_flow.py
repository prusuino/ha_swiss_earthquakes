"""Config flow tests: setup, range checks, duplicate detection, an
unreachable service and the reconfigure flow. The SED query is faked."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sed_earthquakes.config_flow import validate_input
from custom_components.sed_earthquakes.const import (
    CONF_DAYS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MIN_MAGNITUDE,
    CONF_RADIUS_KM,
    DOMAIN,
)

INPUT = {CONF_LATITUDE: 46.948, CONF_LONGITUDE: 7.447, CONF_RADIUS_KM: 150, CONF_MIN_MAGNITUDE: 1.0, CONF_DAYS: 30}


@pytest.fixture
def fake_sed():
    with patch("custom_components.sed_earthquakes.config_flow.async_fetch_quakes", return_value={}):
        yield


def test_range_checks():
    assert validate_input(INPUT) == {}
    assert validate_input({**INPUT, CONF_LATITUDE: 95}) == {CONF_LATITUDE: "invalid_latitude"}
    assert validate_input({**INPUT, CONF_LONGITUDE: -200}) == {CONF_LONGITUDE: "invalid_longitude"}
    assert validate_input({**INPUT, CONF_RADIUS_KM: 0}) == {CONF_RADIUS_KM: "invalid_radius"}
    assert validate_input({**INPUT, CONF_DAYS: 0}) == {CONF_DAYS: "invalid_days"}


async def test_setup(hass: HomeAssistant, enable_custom_integrations, fake_sed) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {**INPUT, CONF_RADIUS_KM: 150.0}
    assert result["result"].unique_id == "46.95_7.45_150.0"


async def test_invalid_radius_is_shown_next_to_the_field(hass: HomeAssistant, enable_custom_integrations, fake_sed) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**INPUT, CONF_RADIUS_KM: 0})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_RADIUS_KM: "invalid_radius"}


async def test_unreachable_service_is_a_form_error(hass: HomeAssistant, enable_custom_integrations) -> None:
    with patch("custom_components.sed_earthquakes.config_flow.async_fetch_quakes", side_effect=TimeoutError()):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_location_twice_is_refused(hass: HomeAssistant, enable_custom_integrations, fake_sed) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id="46.95_7.45_150.0", title="SED", data={**INPUT, CONF_RADIUS_KM: 150.0}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_changes_radius_and_unique_id(hass: HomeAssistant, enable_custom_integrations, fake_sed) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="46.95_7.45_150.0", title="SED", data={**INPUT, CONF_RADIUS_KM: 150.0})
    entry.add_to_hass(hass)
    with patch("custom_components.sed_earthquakes.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
        )
        assert result["step_id"] == "reconfigure"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {**INPUT, CONF_RADIUS_KM: 80, CONF_MIN_MAGNITUDE: 2.0})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.unique_id == "46.95_7.45_80.0"
    assert entry.data[CONF_RADIUS_KM] == 80.0
    assert entry.data[CONF_MIN_MAGNITUDE] == 2.0
