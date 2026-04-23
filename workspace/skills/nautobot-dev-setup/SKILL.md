# SKILL: Nautobot Dev Environment Setup

## Purpose

Deploy a Nautobot development instance using the official `nautobot/nautobot-docker-compose` repository.

## When to Use

- User says "set up a nautobot dev environment" or "deploy nautobot for development"

## CRITICAL RULES — READ THESE FIRST

1. **You MUST clone `https://github.com/nautobot/nautobot-docker-compose.git`** — do NOT create your own docker-compose.yml, Dockerfile, requirements.txt, or setup scripts
2. **You MUST use Poetry 1.5.x** to manage dependencies — `pip install "poetry>=1.5.0,<1.6.0"`. Newer Poetry versions have breaking changes with this repo
3. **You MUST use Invoke** to build and start — do NOT run `docker compose` directly
4. **You MUST install `toml`** in the venv — the tasks.py imports it and will fail without it
5. **Follow the EXACT commands in this file** — do not improvise, do not create your own scripts, do not use pip install for Nautobot or plugins

## Phase 1: Gather Requirements

Ask the user for:

1. **Install location** (default: `~/nautobot-docker-compose`)
2. **Plugins** — present this list:
   - `nautobot-golden-config` — Config compliance (requires nautobot-plugin-nornir)
   - `nautobot-bgp-models` — BGP routing
   - `nautobot-firewall-models` — Firewall policies
   - `nautobot-igp-models` — OSPF configs
   - `nautobot-plugin-nornir` — Nornir integration (REQUIRED by golden-config)
   - `nautobot-ssot` — Single Source of Truth sync
   - `nautobot-device-onboarding` — Device discovery
   - `nautobot-design-builder` — Design templates
   - `welcome-wizard` — Setup wizard
3. **Port** (default: 8080 HTTP)
4. **ipaddr Jinja filter** — yes/no (needed for golden config SVI templates)
5. **Superuser username** (default: admin)

**Wait for answers before proceeding.**

## Phase 2: Clone the Repo

Run these EXACT commands:

```bash
git clone https://github.com/nautobot/nautobot-docker-compose.git <INSTALL_LOCATION>
cd <INSTALL_LOCATION>
```

Verify the repo structure:
```bash
ls -la <INSTALL_LOCATION>/
```

You should see: `pyproject.toml`, `tasks.py`, `Dockerfile`, `config/`, `environments/`, `plugins/`

## Phase 3: Set Up Poetry and Invoke

Poetry 1.5.x is required — newer versions have breaking command syntax.

```bash
pip install "poetry>=1.5.0,<1.6.0"
pip install toml invoke
```

Verify:
```bash
poetry --version
# Should show: Poetry (version 1.5.x)
invoke --version
```

Now set up the Poetry environment:
```bash
cd <INSTALL_LOCATION>
poetry lock
poetry install
```

If `poetry lock` fails with dependency conflicts, try:
```bash
poetry lock --no-update
poetry install
```

## Phase 4: Add Plugins via Poetry

For EACH plugin the user requested, use `poetry add`. Do them all in one command:

```bash
cd <INSTALL_LOCATION>
poetry add <plugin1> <plugin2> <plugin3> ...
```

Example with all common plugins:
```bash
poetry add nautobot-golden-config nautobot-bgp-models nautobot-firewall-models nautobot-igp-models nautobot-plugin-nornir nautobot-ssot nautobot-device-onboarding nautobot-design-builder welcome-wizard
```

If the user wants the ipaddr Jinja filter:
```bash
poetry add netaddr
```

Verify plugins are in pyproject.toml:
```bash
cat pyproject.toml
```

## Phase 5: Configure Environment Files

```bash
cd <INSTALL_LOCATION>
cp environments/local.example.env environments/local.env
cp environments/creds.example.env environments/creds.env
chmod 0600 environments/local.env environments/creds.env
```

Generate secrets and write to `environments/creds.env`:
```bash
DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

cat > environments/creds.env << EOF
NAUTOBOT_DB_PASSWORD=${DB_PASS}
NAUTOBOT_SECRET_KEY=${SECRET_KEY}
NAPALM_USERNAME=
NAPALM_PASSWORD=
NAUTOBOT_GIT_TOKEN=
EOF

chmod 0600 environments/creds.env
```

## Phase 6: Configure invoke.yml

Copy the example and edit it:
```bash
cd <INSTALL_LOCATION>
cp invoke.example.yml invoke.yml
```

The `invoke.yml` file controls the project name and Python version. Read it:
```bash
cat invoke.yml
```

The default should work. If the user wants a custom project name, edit it.

## Phase 7: Configure nautobot_config.py

The config file is at `<INSTALL_LOCATION>/config/nautobot_config.py`.

Read the current file first:
```bash
cat config/nautobot_config.py
```

Then update it to enable the plugins. Find the `PLUGINS` list and replace it with the user's requested plugins. Use the `edit` tool to modify the file.

The PLUGINS list uses Python module names (underscores, not hyphens):

```python
PLUGINS = [
    "nautobot_golden_config",
    "nautobot_bgp_models",
    "nautobot_firewall_models",
    "nautobot_igp_models",
    "nautobot_ssot",
    "nautobot_device_onboarding",
    "nautobot_plugin_nornir",
    "nautobot_design_builder",
    "welcome_wizard",
]
```

Only include plugins the user actually requested.

Add PLUGINS_CONFIG after the PLUGINS list:
```python
PLUGINS_CONFIG = {
    "nautobot_plugin_nornir": {
        "nornir_settings": {
            "credentials": "nautobot_plugin_nornir.plugins.credentials.env_vars.CredentialsEnvVars",
            "runner": {
                "plugin": "threaded",
                "options": {
                    "num_workers": 20,
                },
            },
        },
    },
    "nautobot_golden_config": {
        "per_feature_bar_width": 0.15,
        "per_feature_width": 13,
        "per_feature_height": 4,
        "enable_backup": True,
        "enable_compliance": True,
        "enable_intended": True,
        "enable_sotagg": True,
        "enable_postprocessing": False,
        "sot_agg_transposer": None,
        "platform_slug_map": None,
    },
}
```

If the user wants the ipaddr Jinja filter, add at the END of nautobot_config.py:
```python
import netaddr

def ipaddr(value, query=''):
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

CUSTOM_JINJA_FILTERS = {
    "ipaddr": ipaddr,
}
```

## Phase 8: Build the Custom Container

This builds a Docker image with Nautobot + all plugins baked in. This is why Poetry is required — the Dockerfile reads from `poetry.lock`.

```bash
cd <INSTALL_LOCATION>
invoke build --no-cache
```

This takes several minutes. Wait for it to complete. If it fails:
- Check `poetry lock --check` for dependency issues
- Check Docker is running: `docker ps`
- Check disk space: `df -h`

## Phase 9: Start Nautobot

Start in foreground first to watch for errors:
```bash
cd <INSTALL_LOCATION>
invoke debug
```

Or start as background process:
```bash
invoke start
```

Check container health:
```bash
cd <INSTALL_LOCATION>
invoke cli
# This opens a shell inside the nautobot container
# Type 'exit' to leave
```

Or check with docker:
```bash
docker compose -f environments/docker-compose.postgres.yml -f environments/docker-compose.base.yml -f environments/docker-compose.local.yml ps
```

Wait until all containers show "healthy".

## Phase 10: Create Superuser and API Token

```bash
cd <INSTALL_LOCATION>
invoke createsuperuser
```

This prompts for username, email, and password. Tell the user to enter their credentials.

After superuser is created, tell the user to:
1. Open `http://localhost:8080` in their browser
2. Log in with the superuser credentials
3. Go to Profile → API Tokens → Create Token
4. Copy the token

## Phase 11: Wire NetClaw

Update the project `.env` with the new Nautobot instance:
```
NAUTOBOT_URL=http://localhost:8080
NAUTOBOT_TOKEN=<the_token>
NAUTOBOT_VERIFY_SSL=false
```

Test connectivity using the nautobot-mcp tool:
```
nautobot_test_connection
```

## Plugin Name Reference

| poetry add (hyphens) | PLUGINS entry (underscores) |
|---|---|
| nautobot-golden-config | nautobot_golden_config |
| nautobot-bgp-models | nautobot_bgp_models |
| nautobot-firewall-models | nautobot_firewall_models |
| nautobot-igp-models | nautobot_igp_models |
| nautobot-ssot | nautobot_ssot |
| nautobot-device-onboarding | nautobot_device_onboarding |
| nautobot-plugin-nornir | nautobot_plugin_nornir |
| nautobot-design-builder | nautobot_design_builder |
| welcome-wizard | welcome_wizard |

## Troubleshooting

- **`poetry: command not found`** — run `pip install "poetry>=1.5.0,<1.6.0"`
- **`invoke: command not found`** — run `pip install invoke toml`
- **`ModuleNotFoundError: No module named 'toml'`** — run `pip install toml`
- **`invoke build` fails** — check `poetry lock --check`, ensure Docker is running
- **Container permission errors** — the invoke tasks handle volume permissions; do NOT create volumes manually
- **Port conflict** — change the port in `environments/docker-compose.local.yml`
- **Plugin not found in Nautobot UI** — verify the plugin is in both `pyproject.toml` (poetry add) AND `config/nautobot_config.py` (PLUGINS list)
