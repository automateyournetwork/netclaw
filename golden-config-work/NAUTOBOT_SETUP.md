# Nautobot Server-Side Setup for Golden Config Templates

The SVI template (`_svi.j2`) uses the `ipaddr` Jinja filter to convert CIDR notation (`192.168.3.2/24`) into address + netmask (`192.168.3.2 255.255.255.0`). This filter is not available in Nautobot's Jinja environment by default.

## 1. Install netaddr in the Nautobot Python environment

```bash
# On the Nautobot server (or in the Nautobot container)
pip install netaddr
```

## 2. Register the ipaddr filter in nautobot_config.py

Add the following to your `nautobot_config.py` (typically at `/opt/nautobot/nautobot_config.py` or wherever `NAUTOBOT_CONFIG` points):

```python
# --- Golden Config Jinja Filters ---
import netaddr

def ipaddr(value, query=''):
    """Jinja filter: convert CIDR notation to address or netmask.

    Usage in templates:
      {{ "192.168.3.2/24" | ipaddr('address') }}   -> "192.168.3.2"
      {{ "192.168.3.2/24" | ipaddr('netmask') }}    -> "255.255.255.0"
      {{ "192.168.3.2/24" | ipaddr('network') }}    -> "192.168.3.0"
      {{ "192.168.3.2/24" | ipaddr('prefix') }}     -> 24
    """
    try:
        ip = netaddr.IPNetwork(value)
    except (netaddr.AddrFormatError, ValueError):
        return value
    if query == 'address':
        return str(ip.ip)
    elif query == 'netmask':
        return str(ip.netmask)
    elif query == 'network':
        return str(ip.network)
    elif query == 'prefix':
        return ip.prefixlen
    return str(ip)

# Register with Nautobot's Jinja environment
CUSTOM_JINJA_FILTERS = {
    "ipaddr": ipaddr,
}
```

## 3. Restart Nautobot

```bash
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
# or if using Docker:
docker compose restart nautobot nautobot-worker nautobot-scheduler
```

## 4. Verify

In the Nautobot shell (`nautobot-server shell_plus`):

```python
from jinja2 import Environment
env = Environment()
# The filter should be available in Golden Config's template rendering
```

Or just run a Golden Config intended config job for one device and check that SVIs render with `ip address x.x.x.x y.y.y.y` format.
