"""Runtime string localization (entity names, device info, dashboard content).

Home Assistant's built-in translation system (strings.json / translations/*.json)
only covers config/options flow text. Entity names, device info, the
auto-generated dashboard, and the magnitude scale attribute are set directly
by this integration's Python code and are not covered by that mechanism, so
we do our own minimal lookup here, keyed by hass.config.language. Falls back
to English for any language we don't have strings for.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

SUPPORTED_LANGUAGES = ("de", "en", "fr", "it")

STRINGS: dict[str, dict[str, str]] = {
    "device_name": {
        "de": "SED Erdbeben Schweiz (Umkreis {radius} km)",
        "en": "SED Earthquakes Switzerland (Radius {radius} km)",
        "fr": "Séismes Suisse SED (Rayon {radius} km)",
        "it": "Terremoti Svizzera SED (Raggio {radius} km)",
    },
    "manufacturer": {
        "de": "Schweizerischer Erdbebendienst SED (ETH Zürich)",
        "en": "Swiss Seismological Service SED (ETH Zurich)",
        "fr": "Service Sismologique Suisse SED (EPF Zurich)",
        "it": "Servizio Sismico Svizzero SED (ETH Zurigo)",
    },
    "model": {
        "de": "Erdbebenkatalog (FDSN Event Web Service)",
        "en": "Earthquake Catalog (FDSN Event Web Service)",
        "fr": "Catalogue des séismes (FDSN Event Web Service)",
        "it": "Catalogo dei terremoti (FDSN Event Web Service)",
    },
    "count_sensor_name": {
        "de": "Anzahl Erdbeben",
        "en": "Earthquake Count",
        "fr": "Nombre de séismes",
        "it": "Numero di terremoti",
    },
    "latest_sensor_name": {
        "de": "Letztes Erdbeben",
        "en": "Latest Earthquake",
        "fr": "Dernier séisme",
        "it": "Ultimo terremoto",
    },
    "quake_entity_prefix": {
        "de": "Erdbeben",
        "en": "Earthquake",
        "fr": "Séisme",
        "it": "Terremoto",
    },
    "unknown_place": {
        "de": "Unbekannter Ort",
        "en": "Unknown location",
        "fr": "Lieu inconnu",
        "it": "Luogo sconosciuto",
    },
    "dashboard_title": {
        "de": "Erdbeben Schweiz",
        "en": "Earthquakes Switzerland",
        "fr": "Séismes Suisse",
        "it": "Terremoti Svizzera",
    },
    "map_card_title": {
        "de": "SED Erdbeben Schweiz",
        "en": "SED Earthquakes Switzerland",
        "fr": "Séismes Suisse SED",
        "it": "Terremoti Svizzera SED",
    },
}

# Rough magnitude-impact guidance, based on the SED's own reference values
# (seismo.ethz.ch/en/knowledge/faq/what-does-magnitude-mean). Actual effects
# depend heavily on depth, distance from the epicenter, and ground conditions
# — this is only rough orientation, not a forecast.
MAGNITUDE_SCALE: dict[str, dict[str, str]] = {
    "de": {
        "< 2.5": "Nicht spürbar, nur von Seismometern registriert",
        "2.5 – 4.0": "Von Menschen in Epizentrumsnähe spürbar, in der Regel keine Schäden",
        "4.0 – 4.5": "Vereinzelt leichte Schäden nahe dem Epizentrum möglich (z.B. Risse im Verputz)",
        "4.5 – 5.5": "Leichte Schäden an einzelnen Gebäuden wahrscheinlich, selten auch ernsthaftere Schäden",
        "> 5.5": "In der Schweiz historisch selten (z.B. Basel 1356, M~6.6) — kann erhebliche Schäden verursachen",
        "hinweis": (
            "Grobe Orientierung nach SED-Richtwerten, keine Vorhersage. Tatsächliche "
            "Auswirkungen hängen stark von Tiefe, Distanz zum Epizentrum und Untergrund ab. "
            "Ab Magnitude 3 veröffentlicht der SED i.d.R. eine Schnelleinschätzung."
        ),
    },
    "en": {
        "< 2.5": "Not felt, only registered by seismometers",
        "2.5 – 4.0": "Felt by people near the epicenter, usually no damage",
        "4.0 – 4.5": "Minor damage near the epicenter possible in isolated cases (e.g. cracks in plaster)",
        "4.5 – 5.5": "Minor damage to individual buildings likely, rarely more serious damage",
        "> 5.5": "Historically rare in Switzerland (e.g. Basel 1356, M~6.6) — can cause significant damage",
        "note": (
            "Rough guidance based on SED reference values, not a forecast. Actual effects "
            "depend heavily on depth, distance from the epicenter, and ground conditions. "
            "From magnitude 3, the SED usually publishes a rapid assessment."
        ),
    },
    "fr": {
        "< 2.5": "Non ressenti, uniquement enregistré par les sismomètres",
        "2.5 – 4.0": "Ressenti par les personnes proches de l'épicentre, généralement sans dégâts",
        "4.0 – 4.5": "Dégâts légers ponctuels possibles près de l'épicentre (p. ex. fissures dans le crépi)",
        "4.5 – 5.5": "Dégâts légers probables sur certains bâtiments, rarement des dégâts plus sérieux",
        "> 5.5": "Historiquement rare en Suisse (p. ex. Bâle 1356, M~6.6) — peut causer des dégâts importants",
        "remarque": (
            "Orientation approximative selon les valeurs de référence du SED, pas une "
            "prévision. Les effets réels dépendent fortement de la profondeur, de la distance "
            "à l'épicentre et du sous-sol. À partir de la magnitude 3, le SED publie "
            "généralement une évaluation rapide."
        ),
    },
    "it": {
        "< 2.5": "Non avvertito, registrato solo dai sismometri",
        "2.5 – 4.0": "Avvertito dalle persone vicine all'epicentro, generalmente senza danni",
        "4.0 – 4.5": "Possibili danni lievi isolati vicino all'epicentro (p. es. crepe nell'intonaco)",
        "4.5 – 5.5": "Probabili danni lievi ad alcuni edifici, raramente danni più seri",
        "> 5.5": "Storicamente raro in Svizzera (p. es. Basilea 1356, M~6.6) — può causare danni significativi",
        "nota": (
            "Orientamento approssimativo basato sui valori di riferimento del SED, non una "
            "previsione. Gli effetti reali dipendono fortemente da profondità, distanza "
            "dall'epicentro e sottosuolo. A partire da magnitudo 3, il SED pubblica "
            "generalmente una valutazione rapida."
        ),
    },
}


def get_language(hass: HomeAssistant) -> str:
    lang = (hass.config.language or "en").lower().split("-")[0]
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def t(key: str, hass: HomeAssistant, **kwargs) -> str:
    """Look up a localized string by key, formatted with kwargs."""
    lang = get_language(hass)
    template = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("en") or key
    return template.format(**kwargs) if kwargs else template


def magnitude_scale(hass: HomeAssistant) -> dict[str, str]:
    """Return the magnitude-impact guidance table for the current language."""
    lang = get_language(hass)
    return MAGNITUDE_SCALE.get(lang, MAGNITUDE_SCALE["en"])
