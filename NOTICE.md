# Data Source & Attribution

This integration retrieves earthquake data at runtime from the public **FDSN Event Web Service** of the **Swiss Seismological Service (SED), ETH Zurich** (`arclink.ethz.ch`).

Per the SED's terms of use, citation with a correct statement of the source is required whenever this data is used or displayed, separately from this repository's MIT-licensed source code.

**Required attribution:** *Swiss Seismological Service SED, ETH Zurich*

This integration fulfills that requirement by setting the `attribution` attribute (`"Data: Swiss Seismological Service SED, ETH Zurich"`) on every entity it creates, which Home Assistant surfaces in the entity's "More Info" dialog. If you build dashboards, automations, or republish this data elsewhere, please keep that attribution visible or add your own equivalent notice.

This integration is unofficial and not affiliated with, endorsed by, or supported by the SED or ETH Zurich. It only reads their published data via the standard, international FDSN protocol.

Official SED site: https://www.seismo.ethz.ch/

## Magnitude scale disclaimer

The `magnitude_scale` attribute on `sensor.sed_earthquakes_count_<radius>km` is a rough orientation based on general thresholds published by the SED (see their [magnitude FAQ](https://www.seismo.ethz.ch/en/knowledge/faq/what-does-magnitude-mean/)). It is **not a prediction** — actual effects of any given earthquake depend heavily on depth, distance to the epicenter, and local subsoil conditions.
