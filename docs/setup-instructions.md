# Bare-Metal Install (Ubuntu 24.04)

Prerequisites for running NetClaw without Docker.

## System Packages

```bash
sudo apt update
sudo apt install -y python3-venv curl git
```

## Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## Node.js (via NVM)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash

# Reload shell
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

nvm install --lts
nvm use --lts
```

## Run the Installer

```bash
./scripts/install.sh
```

This handles everything else: OpenClaw, MCP servers, Python deps, skills, and configuration.
