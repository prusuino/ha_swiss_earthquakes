/* Swiss Earthquakes (SED) — dashboard strategy for Home Assistant.
 *
 * The integration serves this file; register it once as a Lovelace resource
 * (Settings → Dashboards → Resources, type "JavaScript module"):
 *
 *     /sed_earthquakes_files/swiss-earthquakes-dashboard.js
 *
 * Then create a dashboard whose raw configuration is
 *
 *     strategy:
 *       type: custom:swiss-earthquakes
 *     views: []
 *
 * Everything below is kept inside one IIFE so its names never collide with
 * another integration shipping the same core in the global scope.
 */
(() => {
/* =====================================================================
 * Dashboard strategy core — shared building blocks
 * =====================================================================
 * A Lovelace dashboard strategy generates a dashboard in the browser at
 * render time. Nothing is written to .storage: the dashboard belongs to
 * the user, the integration only supplies the recipe.
 *
 * ⚠️ This block is duplicated into every integration that ships a
 * strategy. Each integration is its own HACS repository and must not
 * depend on another one being installed, so a shared file is not an
 * option. Keep the copies in sync and bump CORE_VERSION when the shared
 * part changes — it identifies which revision a copy was taken from.
 * ===================================================================== */

const CORE_VERSION = "1.1.0";

/* --- Registry access -------------------------------------------------
 * The registries are the only reliable way to find an integration's
 * entities: entity_id patterns are user-editable, unique_id is not.
 * Both calls are cheap and cached by the frontend for the render pass.
 */
async function loadRegistry(hass) {
  const [entities, devices] = await Promise.all([
    hass.callWS({ type: "config/entity_registry/list" }),
    hass.callWS({ type: "config/device_registry/list" }),
  ]);
  return { entities, devices };
}

/** All registry entries belonging to one integration (platform == domain). */
function entriesOfDomain(entities, domain) {
  return entities.filter((e) => e.platform === domain && !e.disabled_by);
}

/** Registry entries of one config entry, keyed by unique_id suffix.
 *  Mirrors the `f"{entry_id}_{suffix}"` convention the integrations use. */
function bySuffix(entities, configEntryId) {
  const out = {};
  const prefix = `${configEntryId}_`;
  for (const e of entities) {
    if (e.config_entry_id !== configEntryId) continue;
    if (typeof e.unique_id === "string" && e.unique_id.startsWith(prefix)) {
      out[e.unique_id.slice(prefix.length)] = e.entity_id;
    }
  }
  return out;
}

/** Group an integration's entities by the device they belong to.
 *  Returns [{device, entities:[registryEntry,...]}] sorted by device name. */
function groupByDevice(domainEntries, devices) {
  const byId = new Map(devices.map((d) => [d.id, d]));
  const groups = new Map();
  for (const e of domainEntries) {
    if (!e.device_id) continue;
    if (!groups.has(e.device_id)) groups.set(e.device_id, []);
    groups.get(e.device_id).push(e);
  }
  return [...groups.entries()]
    .map(([id, list]) => ({ device: byId.get(id), entities: list }))
    .filter((g) => g.device)
    .sort((a, b) => deviceName(a.device).localeCompare(deviceName(b.device)));
}

function deviceName(device) {
  return device.name_by_user || device.name || "";
}

/* --- Card helpers ---------------------------------------------------- */

const heading = (text, icon, badges) => {
  const card = { type: "heading", heading: text };
  if (icon) card.icon = icon;
  if (badges && badges.length) card.badges = badges;
  return card;
};

const grid = (cards, columnSpan) => {
  const section = { type: "grid", cards: cards.filter(Boolean) };
  if (columnSpan) section.column_span = columnSpan;
  return section;
};

const tile = (entity, extra = {}) => ({ type: "tile", entity, ...extra });

/** Map card fed from the integration's geo_location source.
 *  Deliberately uses geo_location_sources instead of an entity list: the
 *  markers are hidden entities, and the source keeps working when the
 *  set of markers changes between renders.
 *  labelAttribute writes the marker label into the source object, which is
 *  where the map card reads a geo-location source's label config from — the
 *  card-level label_mode only applies to `entities`. */
const mapCard = (domain, opts = {}) => ({
  type: "map",
  geo_location_sources: [
    opts.labelAttribute
      ? { source: domain, label_mode: "attribute", attribute: opts.labelAttribute }
      : domain,
  ],
  entities: opts.entities || ["zone.home"],
  default_zoom: opts.zoom ?? 8,
  theme_mode: "auto",
  grid_options: { columns: 12, rows: opts.rows ?? 6 },
});

/** Shown instead of an empty dashboard — an empty dashboard looks broken
 *  and gives the user nothing to act on. */
const emptyNotice = (text) => ({
  type: "markdown",
  content: text,
});

/* --- Localisation ----------------------------------------------------
 * Strategies run in the frontend, so hass.language is authoritative.
 * Falls back to English for any language the integration does not ship.
 */
function translator(strings, hass) {
  const lang = (hass.language || "en").split("-")[0];
  const table = strings[lang] || strings.en;
  return (key) => (table && table[key]) || (strings.en && strings.en[key]) || key;
}

/* --- Strategy base ---------------------------------------------------
 * Wraps the parts every strategy repeats: load registries, bail out
 * gracefully when the integration is not set up, and hand the concrete
 * strategy a prepared context.
 */

/* Options a user may put under `strategy:` in the raw configuration editor.
 * They are handled here in the core, so every integration supports the same
 * set without shipping its own option code:
 *
 *   map: false        drop the full-screen map view
 *   title: "..."      override the title
 *   max_columns: 3    column count of the generated section views
 *
 * Unknown keys are ignored on purpose - a strategy config is free-form, and a
 * typo should not take the dashboard down. */
const applyViewOptions = (views, config) => {
  const cfg = config || {};
  let out = views;
  if (cfg.map === false) {
    out = out.filter((v) => v.path !== "map");
  }
  const cols = Number(cfg.max_columns);
  if (Number.isFinite(cols) && cols > 0) {
    out = out.map((v) => (v.type === "sections" ? { ...v, max_columns: cols } : v));
  }
  return out;
};

/* A view strategy must return exactly ONE view, while build() yields a list.
 * Section views are merged by concatenating their sections. A panel view (the
 * map) has no sections, so its cards become one full-width section instead -
 * that keeps the map visible rather than silently dropping it. */
const flattenToView = (views, title, icon) => {
  const sections = [];
  for (const v of views) {
    if (Array.isArray(v.sections) && v.sections.length) {
      sections.push(...v.sections);
    } else if (Array.isArray(v.cards) && v.cards.length) {
      sections.push(
        grid(
          v.cards.map((c) => ({
            ...c,
            grid_options: { columns: "full", rows: (c.grid_options || {}).rows ?? 8 },
          }))
        )
      );
    }
  }
  return { title, icon, type: "sections", max_columns: 2, sections };
};

function defineDashboardStrategy(name, { domain, title, icon, build, strings, description }) {
  /* Shared by both strategy flavours: everything up to the finished view list. */
  const buildViews = async (config, hass) => {
    const t = translator(strings || {}, hass);
    let registry;
    try {
      registry = await loadRegistry(hass);
    } catch (err) {
      // Registry unreachable: render a readable message rather than
      // letting the dashboard fail with a blank screen.
      return [{ title: title, cards: [emptyNotice(`\u26a0\ufe0f ${err}`)] }];
    }
    const domainEntries = entriesOfDomain(registry.entities, domain);
    if (!domainEntries.length) {
      return [{ title: title, icon, cards: [emptyNotice(t("not_configured"))] }];
    }
    const views = await build({
      hass,
      config,
      t,
      domain,
      entities: domainEntries,
      devices: registry.devices,
      allEntities: registry.entities,
      helpers: { heading, grid, tile, mapCard, emptyNotice, bySuffix, groupByDevice, deviceName },
    });
    return applyViewOptions(views, config);
  };

  class Strategy extends HTMLElement {
    static async generate(config, hass) {
      const views = await buildViews(config, hass);
      return { title: (config && config.title) || title, views };
    }
  }

  /* The view flavour: fills a single view of a dashboard the user built
   * themselves, so adjusting the layout no longer requires "take control". */
  class ViewStrategy extends HTMLElement {
    static async generate(config, hass) {
      const views = await buildViews(config, hass);
      return flattenToView(views, (config && config.title) || title, icon);
    }
  }

  // getCreateSuggestions lets Home Assistant offer sensible defaults when the
  // strategy is picked from the "new dashboard" dialog.
  Strategy.getCreateSuggestions = () => ({ title, icon });

  customElements.define(`ll-strategy-dashboard-${name}`, Strategy);
  customElements.define(`ll-strategy-view-${name}`, ViewStrategy);

  // Announce the strategy to the frontend so it appears in the dashboard
  // creation dialog instead of having to be typed into the raw editor.
  window.customStrategies = window.customStrategies || [];
  if (!window.customStrategies.some((s) => s.type === name)) {
    window.customStrategies.push({
      type: name,
      strategyType: "dashboard",
      name: title,
      description: description || "",
    });
  }
  return Strategy;
}


/* =====================================================================
 * Dashboard strategy: Swiss Earthquakes (SED)
 * =====================================================================
 * Generates the dashboard in the browser at render time. Versions before
 * 1.3.0 created an "Earthquakes Switzerland" dashboard in the user's
 * Lovelace storage; 1.3.0 removed that without a replacement. A strategy
 * produces the same map — plus an overview per configured location —
 * without writing anything into the user's configuration.
 *
 * It also keeps itself current: adding a second location (a further config
 * entry) adds its section on the next load; removing one leaves nothing
 * behind.
 *
 * Usage — create an empty dashboard, open the raw configuration editor and
 * replace its content with:
 *
 *     strategy:
 *       type: custom:swiss-earthquakes
 *     views: []
 * ===================================================================== */

const SEQ_STRINGS = {
  en: {
    map: "Map",
    overview: "Overview",
    latest: "Latest earthquake",
    strongest: "Strongest earthquake",
    no_quakes: "No earthquakes in the configured time window.",
    attribution: "Data: Swiss Seismological Service SED, ETH Zurich",
    not_configured:
      "### Swiss Earthquakes (SED) is not set up yet\n\nAdd the integration under **Settings → Devices & services** first. This dashboard then fills itself — there is nothing to configure here.",
  },
  de: {
    map: "Karte",
    overview: "Übersicht",
    latest: "Letztes Erdbeben",
    strongest: "Stärkstes Erdbeben",
    no_quakes: "Keine Erdbeben im eingestellten Zeitfenster.",
    attribution: "Daten: Schweizerischer Erdbebendienst SED, ETH Zürich",
    not_configured:
      "### Swiss Earthquakes (SED) ist noch nicht eingerichtet\n\nFüge die Integration zuerst unter **Einstellungen → Geräte & Dienste** hinzu. Dieses Dashboard füllt sich danach von selbst — hier ist nichts einzustellen.",
  },
  fr: {
    map: "Carte",
    overview: "Aperçu",
    latest: "Dernier séisme",
    strongest: "Séisme le plus fort",
    no_quakes: "Aucun séisme dans la fenêtre temporelle configurée.",
    attribution: "Données : Service Sismologique Suisse SED, EPF Zurich",
    not_configured:
      "### Swiss Earthquakes (SED) n'est pas encore configuré\n\nAjoutez d'abord l'intégration sous **Paramètres → Appareils et services**. Ce tableau de bord se remplit ensuite tout seul.",
  },
  it: {
    map: "Mappa",
    overview: "Panoramica",
    latest: "Ultimo terremoto",
    strongest: "Terremoto più forte",
    no_quakes: "Nessun terremoto nella finestra temporale configurata.",
    attribution: "Dati: Servizio Sismico Svizzero SED, ETH Zurigo",
    not_configured:
      "### Swiss Earthquakes (SED) non è ancora configurato\n\nAggiungi prima l'integrazione in **Impostazioni → Dispositivi e servizi**. Questa dashboard si riempie poi da sola.",
  },
};

/* Text card for one location: the latest earthquake's one-line summary and
 * the strongest event of the window. The summary is a long free-text state
 * ("place · M x.x · date"), which a tile would truncate — a markdown card
 * shows it in full. The template also turns the sensor's unknown state,
 * which is what a quiet period looks like, into a readable sentence. */
const SEQ_summaryCard = (t, summaryId, countId) => {
  const lines = [
    `{% set s = states('${summaryId}') %}`,
    "{% if s in ['unknown', 'unavailable'] %}",
    `_${t("no_quakes")}_`,
    "{% else %}",
    `**${t("latest")}:** {{ s }}`,
  ];
  if (countId) {
    // strongest_quake is a dict attribute of the count sensor; magnitude
    // can be missing for events the SED has not rated yet.
    lines.push(
      `{% set q = state_attr('${countId}', 'strongest_quake') %}`,
      "{% if q %}",
      "",
      `**${t("strongest")}:** {{ q.place }}{% if q.magnitude is not none %} · M {{ '%.1f'|format(q.magnitude) }}{% endif %}`,
      "{% endif %}"
    );
  }
  lines.push("{% endif %}");
  return { type: "markdown", content: lines.join("\n"), grid_options: { columns: "full" } };
};

defineDashboardStrategy("swiss-earthquakes", {
  domain: "sed_earthquakes",
  title: "Swiss Earthquakes",
  icon: "mdi:vibrate",
  description:
    "Map of recent earthquakes labeled with their magnitude, plus count, latest and strongest event per configured location.",
  strings: SEQ_STRINGS,

  async build({ t, domain, entities, devices, helpers }) {
    const { heading, grid, tile, mapCard, groupByDevice, deviceName, bySuffix } = helpers;
    const views = [];

    // --- Map ----------------------------------------------------------
    // Shown whenever the integration is set up, not only while markers
    // exist: the map selects the markers by source, and in a quiet period
    // there are simply no earthquakes to draw — an empty map is still the
    // right picture. This is the map card the integration used to create.
    views.push({
      title: t("map"),
      path: "map",
      icon: "mdi:map-marker-radius",
      type: "panel",
      cards: [mapCard(domain, { zoom: 8, rows: 12, labelAttribute: "magnitude" })],
    });

    // --- One section per config entry ---------------------------------
    // Each location (config entry) is its own device carrying the three
    // sensors; the markers have no device and are left to the map. Suffix
    // lookup mirrors the integration's unique_id scheme, so a user-renamed
    // entity_id keeps working.
    const sections = [];
    for (const group of groupByDevice(entities, devices)) {
      const entryId = group.entities.find((e) => e.config_entry_id)?.config_entry_id;
      if (!entryId) continue;
      const ids = bySuffix(entities, entryId);
      const hidden = new Set(group.entities.filter((e) => e.hidden_by).map((e) => e.entity_id));
      const visible = (entityId) => entityId && !hidden.has(entityId);

      const countId = visible(ids.count) ? ids.count : null;
      const latestId = visible(ids.latest) ? ids.latest : null;
      const summaryId = visible(ids.latest_summary) ? ids.latest_summary : null;

      const cards = [
        countId && tile(countId, { grid_options: { columns: 6 } }),
        latestId && tile(latestId, { grid_options: { columns: 6 } }),
        summaryId && SEQ_summaryCard(t, summaryId, countId),
      ].filter(Boolean);
      if (!cards.length) continue;
      sections.push(grid([heading(deviceName(group.device), "mdi:vibrate"), ...cards]));
    }

    if (sections.length) {
      // The SED's terms require the source to be cited wherever its data is
      // shown; every entity carries it as attribution, the dashboard shows
      // it once at the bottom.
      sections.push(
        grid([{ type: "markdown", text_only: true, content: t("attribution") }], 2)
      );
      views.push({
        title: t("overview"),
        path: "overview",
        icon: "mdi:view-dashboard-outline",
        type: "sections",
        max_columns: 2,
        sections,
      });
    }

    return views;
  },
});
})();
