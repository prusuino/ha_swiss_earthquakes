"""Constants for the Swiss Earthquakes (SED) integration."""
DOMAIN = "sed_earthquakes"

# TLS endpoint of the same SED FDSN service. The arclink host serves
# identical data but has no TLS listener, so it cannot simply be upgraded
# to https. Magnitudes and coordinates drive user automations and must not
# be modifiable in transit.
FDSN_URL = "https://eida.ethz.ch/fdsnws/event/1/query"
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
