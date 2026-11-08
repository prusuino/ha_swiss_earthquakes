"""Pure helpers of the coordinator: the FDSN text parser, the distance and
the error descriptions that keep coordinates out of the log."""
from __future__ import annotations

from types import SimpleNamespace

import aiohttp

from custom_components.sed_earthquakes.coordinator import (
    _haversine_km,
    _parse_fdsn_text,
    classify_error,
    describe_error,
)

HASS = SimpleNamespace(config=SimpleNamespace(language="en"))

FDSN_TEXT = """#EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName
smi:ch.ethz.sed/sc20a/Event/2026/11/08/abc|2026-11-08T22:14:03.1Z|46.9517|7.4389|8.2|SED|SED||SED|MLhc|2.31|SED|Bern BE
smi:ch.ethz.sed/sc20a/Event/2026/11/08/def|2026-11-08T20:01:00.0Z|47.3769|8.5417|12.75|SED|SED||SED|MLhc|1.0|SED|
broken|line|with|too|few|columns
smi:ch.ethz.sed/sc20a/Event/2026/11/08/ghi|2026-11-08T19:00:00.0Z|not-a-number|8.5|5|SED|SED||SED|MLhc|1.5|SED|Nowhere
"""


def test_parser_builds_one_record_per_event():
    quakes = _parse_fdsn_text(FDSN_TEXT, 46.948, 7.447, HASS)
    assert len(quakes) == 2  # the broken rows are skipped
    bern = quakes["smi:ch.ethz.sed/sc20a/Event/2026/11/08/abc"]
    assert bern["magnitude"] == 2.31
    assert bern["depth_km"] == 8.2
    assert bern["magnitude_type"] == "MLhc"
    assert bern["place"] == "Bern BE"
    assert bern["distance_km"] < 1.0
    zurich = quakes["smi:ch.ethz.sed/sc20a/Event/2026/11/08/def"]
    assert zurich["depth_km"] == 12.8  # rounded to one decimal
    assert zurich["place"]  # empty location name gets the localized fallback
    assert zurich["place"] != ""
    assert 90 < zurich["distance_km"] < 100


def test_parser_tolerates_an_empty_answer():
    assert _parse_fdsn_text("", 46.9, 7.4, HASS) == {}
    assert _parse_fdsn_text("#EventID|Time|Latitude|Longitude\n", 46.9, 7.4, HASS) == {}


def test_haversine_bern_zurich():
    assert round(_haversine_km(46.948, 7.447, 47.377, 8.540)) == 95


def test_error_descriptions_hide_the_request_url():
    request = SimpleNamespace(real_url="https://example.invalid/fdsnws?latitude=46.9&longitude=7.4", headers={})
    err = aiohttp.ClientResponseError(request, (), status=503, message="Service Unavailable")
    assert classify_error(err) == "http"
    assert describe_error(err) == "HTTP 503 Service Unavailable"
    assert "latitude" not in describe_error(err)
    assert classify_error(TimeoutError()) == "timeout"
    assert describe_error(TimeoutError()) == "timeout"
    assert classify_error(RuntimeError("x")) == "connection"
    assert describe_error(RuntimeError("x")) == "RuntimeError: x"
