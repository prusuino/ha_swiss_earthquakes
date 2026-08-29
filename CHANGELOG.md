# Changelog

## 1.3.0 — 2026-08-29

**Breaking:** the integration no longer creates an "Earthquakes Switzerland" dashboard for you. It wrote directly into Home Assistant's internal Lovelace storage, which could silently discard the entry again and recreated the dashboard even after a user had deliberately deleted it. Dashboards are now left entirely to the user. An existing dashboard from an earlier version is kept and kept working — nothing is deleted on update. The README explains how to add the built-in Map card in three steps; the card configuration is unchanged, so an existing dashboard needs no adjustment.

- Revised earthquakes are now applied. The SED corrects magnitude, location and depth after manual review; until now an event kept the values it was first published with, which also left its map marker at the outdated position. Known events now follow those revisions, including magnitude, icon, coordinates, distance, depth and time.
- Earthquake data is now fetched over HTTPS (`eida.ethz.ch`) instead of cleartext HTTP. Same official SED FDSN service, same data — but magnitudes and coordinates that automations act on can no longer be altered in transit.
- Entities that a user made visible by hand are no longer hidden again on every restart. New entities are still hidden by default so they don't flood the auto-generated overview map; existing ones are no longer rewritten.
- Added the missing English translation file. English users saw raw translation keys instead of field labels throughout the setup dialog.

## 1.2.0 — 2026-07-24

- New sensor `sensor.sed_earthquakes_latest_summary_<radius>km`: human-readable one-line summary of the most recent earthquake — "place · M magnitude · date/time" (localized date format) — for glanceable dashboard tiles. Full details (place, magnitude, time, depth, distance, event ID) as attributes. For automations, keep triggering on the timestamp sensor `sensor.sed_earthquakes_latest_<radius>km`.

## 1.1.0 — 2026-07-18

- Earthquake markers no longer appear on Home Assistant's auto-generated default dashboard map (which draws every geo_location entity in the system). They remain fully visible on the integration's own dashboard map card. Existing installations are migrated automatically; a user's own explicit show/hide choice in the entity registry is never overridden.

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
