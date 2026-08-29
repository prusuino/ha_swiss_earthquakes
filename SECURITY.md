# Security Policy

## Supported Versions

Only the latest release is supported. Please update to the latest version before reporting an issue.

## Reporting a Vulnerability

This integration only reads publicly published data from its official Swiss data source over HTTPS — it handles no credentials and has no write access to any external system.

What it sends is the query itself: with every refresh (every 10 minutes) and once during setup, the configured latitude and longitude, the radius, the minimum magnitude and the time window go to `https://eida.ethz.ch/fdsnws/event/1/query` as URL query parameters, over TLS, without any identifiers or cookies. Nothing else leaves your instance. The coordinates default to your Home Assistant home location at full precision; if you consider them sensitive, enter them rounded to two decimals (about 1 km) — the radius makes that difference irrelevant. A failed request is logged with its HTTP status (or the error type), not with the URL.

If you still believe you have found a security issue (e.g. in how data is parsed or how entities are exposed), please report it privately via [GitHub Security Advisories](../../security/advisories/new) rather than opening a public issue.

For anything that is not security-sensitive (bugs, feature requests), please use the regular [Issues](../../issues) tab instead.
