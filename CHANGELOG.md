# Changelog

## 1.5.0 — 2026-08-29

- **Changed: the sensors' suggested entity ids carry a short tag of the config entry** — the last four characters of the entry id, lower-cased, after the radius: `sensor.sed_earthquakes_count_150km_7f3a`, `sensor.sed_earthquakes_latest_150km_7f3a`, `sensor.sed_earthquakes_latest_summary_150km_7f3a`. The radius alone did not tell two entries apart: a second entry at another location with the same radius (a home and a holiday location, say) suggested the very same ids, which Home Assistant resolved by appending `_2` to whichever entry loaded second, so an automation copied between the entries silently targeted the wrong one. A suggested id only applies when an entity is first created, so **the sensors of existing entries keep the ids they have** — unique ids are unchanged, nothing is renamed, and there is nothing to do on upgrade. The README entity table shows the pattern.
- **Changed: map markers get a language-neutral entity id.** A new marker is created as `geo_location.sed_earthquake_<event>_<tag>` (`geo_location.sed_earthquake_2026nuuviw_7f3a`), built from the SED event id and the entry tag, instead of an id derived from its localized name (`geo_location.erdbeben_m2_3_sion_vs` on a German instance, `geo_location.earthquake_m2_3_sion_vs` on an English one). The id is the same in every language and does not change when the SED revises the event. **Markers that already exist keep their ids** until their earthquake ages out of the time window; only markers of new earthquakes get the new form. The friendly name is unchanged and still localized, and addressing markers by their `source` attribute, as the README recommends, works for both.
- **New: the setup form checks its values and the connection.** A radius of 0, a time window under a day and coordinates outside the valid range are rejected with a message next to the field instead of creating an entry that fails on its first refresh, and one query goes to the SED service before the entry is created, so an unreachable service shows up in the form (*The SED service could not be reached*) rather than as a failed setup afterwards.
- **Fixed: the dashboard strategy's text card says when the SED service is unreachable.** While the sensors were unavailable it read *No earthquakes in the configured time window*, as if the period were quiet; it now shows that the earthquake data is unavailable, in all four languages.
- Documented what the integration sends: with every refresh, the configured latitude and longitude, radius, minimum magnitude and time window go to the SED service as query parameters over HTTPS — nothing else, and no identifiers. SECURITY.md and the README now say so, with the tip to enter rounded coordinates if the exact home location should not leave your instance. A failed request is logged with its HTTP status only; the request URL, which carries the coordinates, no longer appears in the log.
- Documented: each refresh asks the SED service for at most 200 events, newest first, so in a busy period with a large radius, a low minimum magnitude and a long time window the oldest events of the window are left out.
- Changed: the device name shows the radius without a trailing `.0` (*Radius 150 km* instead of *Radius 150.0 km*), matching the entity ids. The titles of existing entries in the integrations list keep their original text.
- Changed: only connection and HTTP errors are reported as *SED earthquake data unreachable*; any other failure during a refresh is logged with its traceback instead of being disguised as a connection problem.
- Updated the bundled dashboard-strategy core to 1.1.1: `map: false` now also removes a map section inside a view, `max_columns` is honoured in the view-strategy flavour, and a view's header is kept when the strategy fills a single view.

## 1.4.0 — 2026-08-29

- **Fixed: the map markers of two overlapping entries no longer collide.** A marker's unique id was the SED event id alone, so when a second entry covered some of the same earthquakes (a home and a holiday location whose radii overlap, say), Home Assistant rejected that entry's markers for the shared events as duplicates — they were silently missing from its map, with nothing but a log line. The unique id now includes the config entry. **Existing markers are migrated automatically on the first start**: each entry's registry entries are moved to the new unique id in place, so entity ids, history, and anything you changed on a marker (name, visibility, area) are kept. Nothing to do on your side.
- **Fixed: map markers go unavailable while the SED service is unreachable**, as the sensors already did. Until now a marker kept showing its last known label indefinitely, however stale the data behind it was; it now follows the sensors and comes back on the next successful refresh.
- **Fixed: markers of expired earthquakes no longer linger in the entity registry.** When an earthquake aged out of the time window, its entity was removed but its entity-registry entry was left behind, so after the next restart every such event was back as an `unavailable` entity flagged `restored` — and stayed, since an expired event never returns; on a long-running installation these soon outnumbered the live markers. Expired events are now removed from the entity registry too, and **existing leftovers are cleaned up once on the next start** (markers of earthquakes that expire while Home Assistant is off are handled the same way). Markers of earthquakes still in the window are untouched, including anything you changed on them. Nothing to do on your side.
- **New: a dashboard strategy** replaces the automatic dashboard that 1.3.0 removed without a substitute. A strategy is a recipe Home Assistant renders in the browser: it stores nothing, overwrites nothing, and reflects your current setup on every page load — a second location gets its own section by itself, a removed one disappears with no leftover card. It renders the same full-screen map as before (markers labeled with the magnitude, shown even while no earthquake is in the time window) plus an overview per configured location: the earthquake count and the time of the latest event as tiles, and a text card with the latest and the strongest earthquake. Setup is in the README; in short, a new dashboard with:

  ```yaml
  strategy:
    type: custom:swiss-earthquakes
  views: []
  ```

  The strategy also appears in the **+ Add dashboard** dialog, honours `title`, `max_columns` and `map: false` under `strategy:`, and can fill a single view of an existing dashboard (`views: - strategy: {type: custom:swiss-earthquakes}`). Its texts follow the Home Assistant language (German, English, French, Italian).
- **One-time step:** the integration serves the strategy file at `/sed_earthquakes_files/swiss-earthquakes-dashboard.js` but does not register it as a Lovelace resource — the resource list is part of your dashboard configuration, and nothing is written there. Add it once under **Settings → Dashboards → ⋮ → Resources** (type *JavaScript module*); the README has the details. The map card snippet from the README keeps working unchanged, and an existing dashboard needs no adjustment.
- Changed: the minimum Home Assistant version is now **2025.4.0** (previously 2024.1.0). The file is served through `async_register_static_paths` (added in 2024.7), and the dashboard it builds uses the heading card (2024.10), `grid_options` card sizing (2024.11), the markdown card's `text_only` option (2025.3) and attribute labels on geo-location sources of the map card (2025.4) — older releases render the map, but without the magnitude label on the markers.
- Added `http` to the integration's dependencies, since it now serves a file.
- Documented: a map marker's entity id follows its localized name (`geo_location.erdbeben_…` on a German instance, `geo_location.earthquake_…` on an English one), so it differs between installations. The README now shows how to address markers independently of the language — the map card's `geo_location_sources` and the `source` attribute in templates.
- README: the installation instructions now describe the HACS default listing, with a My Home Assistant button that opens the integration directly in HACS.

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
