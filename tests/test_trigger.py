"""The trigger "Earthquake detected" with real automations, on a registered
latest-earthquake sensor whose state is set by hand: a new event, the first
event after a quiet time, an outage, the minimum magnitude."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.sed_earthquakes import trigger
from custom_components.sed_earthquakes.const import DOMAIN

FIRST = "2026-11-23T10:00:00+00:00"
SECOND = "2026-11-23T14:30:00+00:00"
THIRD = "2026-11-23T18:45:00+00:00"


def _latest(hass: HomeAssistant, platform: str = DOMAIN, name: str = "latest") -> str:
    reg = er.async_get(hass).async_get_or_create("sensor", platform, f"entry_{name}", suggested_object_id=name, original_device_class="timestamp")
    return reg.entity_id


def _set(hass: HomeAssistant, entity_id: str, state: str, magnitude: float | None = 2.4) -> None:
    hass.states.async_set(entity_id, state, {"device_class": "timestamp", "magnitude": magnitude})


async def _automation(hass: HomeAssistant, entity_ids, **options) -> list:
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(hass, "automation", {"automation": {
        "alias": "Tell me",
        "trigger": {"trigger": "sed_earthquakes.earthquake_detected", "target": {"entity_id": entity_ids}, "options": options},
        "action": {"action": "test.automation"},
    }})
    await hass.async_block_till_done()
    assert hass.states.get("automation.tell_me") is not None, "the automation was rejected"
    return calls


async def test_a_new_event_fires_and_other_integrations_are_ignored(hass: HomeAssistant, enable_custom_integrations) -> None:
    assert set(await trigger.async_get_triggers(hass)) == {"earthquake_detected"}
    latest = _latest(hass)
    foreign = _latest(hass, "another_integration", "backup")
    _set(hass, latest, FIRST)
    _set(hass, foreign, FIRST)
    calls = await _automation(hass, [latest, foreign])
    _set(hass, foreign, SECOND)  # not ours
    await hass.async_block_till_done()
    assert len(calls) == 0
    _set(hass, latest, SECOND)
    await hass.async_block_till_done()
    assert len(calls) == 1
    _set(hass, latest, SECOND, magnitude=2.6)  # the same event, revised: no new earthquake
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_the_first_earthquake_after_a_quiet_time_fires(hass: HomeAssistant, enable_custom_integrations) -> None:
    latest = _latest(hass)
    hass.states.async_set(latest, "unknown", {"device_class": "timestamp"})  # nothing in the time window
    calls = await _automation(hass, latest)
    _set(hass, latest, FIRST)
    await hass.async_block_till_done()
    assert len(calls) == 1
    hass.states.async_set(latest, "unknown", {"device_class": "timestamp"})  # it aged out of the window
    await hass.async_block_till_done()
    assert len(calls) == 1
    _set(hass, latest, SECOND)
    await hass.async_block_till_done()
    assert len(calls) == 2


async def test_an_outage_fires_only_for_a_new_event(hass: HomeAssistant, enable_custom_integrations) -> None:
    latest = _latest(hass)
    _set(hass, latest, FIRST)
    calls = await _automation(hass, latest)
    _set(hass, latest, SECOND)
    await hass.async_block_till_done()
    assert len(calls) == 1

    hass.states.async_set(latest, "unavailable")
    await hass.async_block_till_done()
    _set(hass, latest, SECOND)  # the SED is back with the same event
    await hass.async_block_till_done()
    assert len(calls) == 1

    hass.states.async_set(latest, "unavailable")
    await hass.async_block_till_done()
    _set(hass, latest, THIRD)  # recorded during the outage
    await hass.async_block_till_done()
    assert len(calls) == 2


async def test_nothing_known_before_an_outage_stays_quiet(hass: HomeAssistant, enable_custom_integrations) -> None:
    latest = _latest(hass)
    hass.states.async_set(latest, "unavailable", {"device_class": "timestamp"})
    calls = await _automation(hass, latest)  # the automation starts during an outage
    _set(hass, latest, FIRST)  # an event of unknown age: no reason to announce it
    await hass.async_block_till_done()
    assert len(calls) == 0
    _set(hass, latest, SECOND)
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_minimum_magnitude(hass: HomeAssistant, enable_custom_integrations) -> None:
    latest = _latest(hass)
    hass.states.async_set(latest, "unknown", {"device_class": "timestamp"})
    calls = await _automation(hass, latest, minimum_magnitude=3.0)
    _set(hass, latest, FIRST, magnitude=2.9)
    await hass.async_block_till_done()
    _set(hass, latest, SECOND, magnitude=None)  # not rated yet
    await hass.async_block_till_done()
    assert len(calls) == 0
    _set(hass, latest, THIRD, magnitude=3.4)
    await hass.async_block_till_done()
    assert len(calls) == 1
    # a strong first event after a quiet time
    hass.states.async_set(latest, "unknown", {"device_class": "timestamp"})
    await hass.async_block_till_done()
    _set(hass, latest, "2026-11-24T02:00:00+00:00", magnitude=4.1)
    await hass.async_block_till_done()
    assert len(calls) == 2
