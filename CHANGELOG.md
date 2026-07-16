# Changelog

## 1.0.0 — 2026-07-16

Initial public release.

- `geo_location.earthquake_<magnitude>_<place>` — one entity per currently tracked earthquake, shown automatically on Home Assistant's built-in Map card
- `sensor.sed_earthquakes_count_<radius>km` — count of earthquakes in the configured radius/time window/magnitude threshold, with the strongest current event and a localized magnitude-scale reference as attributes
- `sensor.sed_earthquakes_latest_<radius>km` — timestamp of the most recent earthquake, so automations can reliably trigger on a new event
- Automatic dashboard setup with a native Map card showing each earthquake's magnitude directly on its marker
- Multi-language support (German, English, French, Italian) for entity names, device info, the dashboard, and the magnitude scale text, based on the Home Assistant language setting
- Config flow: location (defaults to Home Assistant's home location), radius (km), minimum magnitude, time window (days); supports multiple locations/radii via multiple config entries
- Data sourced from the SED's public FDSN Event Web Service (no API key required), refreshed every 10 minutes
- Quarry blasts filtered out server-side, only real earthquakes shown
- All entities carry the required SED data attribution
