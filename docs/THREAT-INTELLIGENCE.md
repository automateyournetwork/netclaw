# Threat intelligence tools

Install either optional component with `scripts/install.sh --add greynoise-community` or `scripts/install.sh --add threatintel`. Both advertise tools over stdio. A lookup sends its indicator to the corresponding external provider.

## GreyNoise Community

Call `greynoise_community_lookup` with a publicly routable IPv4 address. A 404 means GreyNoise has no record for that address. A 429 means the provider rate limit was reached. The API accepts an optional `GREYNOISE_API_KEY`. Set `GREYNOISE_TIMEOUT` to override the default ten-second request timeout (maximum sixty). [Community API](https://docs.greynoise.io/reference/getcommunityip)

## Community threat intelligence

The installer builds the [reviewed community server](https://github.com/aplaceforallmystuff/mcp-threatintel/tree/1f36c2d29877124bd60ac1fe4562b203e3fd3a14) with its npm lockfile. `threatintel_status` reports the providers available in this installation. GreyNoise Community and Feodo Tracker are available without credentials. Set the relevant optional key in the selected runtime environment to enable additional providers.

| Variable | Provider |
| --- | --- |
| GREYNOISE_API_KEY | GreyNoise |
| OTX_API_KEY | AlienVault OTX |
| ABUSEIPDB_API_KEY | AbuseIPDB |
| ABUSECH_AUTH_KEY | abuse.ch URLhaus, ThreatFox and MalwareBazaar |
