"""Constants for the Swiss Earthquakes (SED) integration."""
DOMAIN = "sed_earthquakes"

FDSN_URL = "http://arclink.ethz.ch/fdsnws/event/1/query"
KM_PER_DEGREE = 111.0
UPDATE_INTERVAL_MINUTES = 10

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RADIUS_KM = "radius_km"
CONF_MIN_MAGNITUDE = "min_magnitude"
CONF_DAYS = "days"

DEFAULT_RADIUS_KM = 150
DEFAULT_MIN_MAGNITUDE = 0.0
DEFAULT_DAYS = 30
