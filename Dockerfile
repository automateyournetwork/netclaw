FROM ubuntu:25.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NVM_DIR=/usr/local/nvm \
    NODE_VERSION=24 \
    OPENCLAW_HOME=/root \
    NETCLAW_DIR=/opt/netclaw

# System deps + Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    git curl ca-certificates tshark nmap graphviz sudo build-essential \
    openssh-client sshpass docker.io \
    && rm -rf /var/lib/apt/lists/*

# Node.js via nvm
RUN mkdir -p $NVM_DIR \
    && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" && nvm install $NODE_VERSION && nvm alias default $NODE_VERSION
ENV PATH="$NVM_DIR/versions/node/v24.15.0/bin:$PATH"

# OpenClaw
RUN npm install -g openclaw@latest

# uv/uvx for AWS/Grafana/etc MCP servers
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# gtrace binary
RUN ARCH=$(dpkg --print-architecture) \
    && GTRACE_VER=$(curl -sL https://api.github.com/repos/hervehildenbrand/gtrace/releases/latest | grep -oP '"tag_name":\s*"\K[^"]+' || echo "v0.9.7") \
    && GTRACE_VER_NUM="${GTRACE_VER#v}" \
    && curl -sL "https://github.com/hervehildenbrand/gtrace/releases/download/${GTRACE_VER}/gtrace_${GTRACE_VER_NUM}_linux_${ARCH}.tar.gz" \
       | tar xz -C /usr/local/bin gtrace 2>/dev/null || true

# nmap + gtrace raw socket caps
RUN setcap cap_net_raw+ep /usr/bin/nmap 2>/dev/null || true \
    && [ -f /usr/local/bin/gtrace ] && setcap cap_net_raw+ep /usr/local/bin/gtrace 2>/dev/null || true

WORKDIR $NETCLAW_DIR

# Python deps — install in a venv to avoid Ubuntu's externally-managed restriction
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements-docker.txt .
RUN pip install --upgrade pip && pip install -r requirements-docker.txt

# Copy project
COPY . .

# Install cloned MCP servers that need editable/pip install
RUN cd mcp-servers/mcp-nvd && pip install -e . 2>/dev/null || true \
    && cd $NETCLAW_DIR \
    && cd mcp-servers/junos-mcp-server && pip install . 2>/dev/null || true \
    && cd $NETCLAW_DIR \
    && cd mcp-servers/fwrule-mcp && pip install -e . 2>/dev/null || true \
    && cd $NETCLAW_DIR \
    && cd mcp-servers/mempalace && pip install -e . 2>/dev/null || true \
    && cd $NETCLAW_DIR \
    && cd mcp-servers/AAP-Enterprise-MCP-Server && pip install -e . 2>/dev/null || true \
    && cd $NETCLAW_DIR \
    && cd mcp-servers/mcp-nautobot && pip install -e . 2>/dev/null || true \
    && cd $NETCLAW_DIR \
    && pip install -r mcp-servers/nautobot-mcp-v2/requirements.txt 2>/dev/null || true \
    && cd $NETCLAW_DIR

# Build markmap (Node MCP server)
RUN cd mcp-servers/markmap_mcp/markmap-mcp && npm install && npm run build && cd $NETCLAW_DIR

# Build NetClaw Visual HUD
RUN cd ui/netclaw-visual && npm install && npm run build && cd $NETCLAW_DIR

# Pre-cache npx packages
RUN npm cache add @drawio/mcp @mjpitz/mcp-rfc @anthropic-ai/microsoft-graph-mcp @zereight/mcp-gitlab 2>/dev/null || true

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# SSH config for legacy network devices (older IOS-XE, NX-OS, etc.)
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh && \
    printf 'Host *\n    KexAlgorithms +diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1\n    HostKeyAlgorithms +ssh-rsa\n    PubkeyAcceptedAlgorithms +ssh-rsa\n    StrictHostKeyChecking no\n    UserKnownHostsFile /dev/null\n' > /root/.ssh/config && \
    chmod 600 /root/.ssh/config

EXPOSE 18789 3000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gateway"]
