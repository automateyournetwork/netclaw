FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc curl\
    && rm -rf /var/lib/apt/lists/*


# Copy application files
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml .


# Create non-root user first
RUN useradd -m -u 1000 mcpuser

# Install dependencies from root (workspace context)
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONOPTIMIZE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN uv sync && chown -R mcpuser:mcpuser /app

USER mcpuser

# Expose MCP port
EXPOSE 8000

# Run application from root with proper Python path
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Pre-compile the app code to greatly reduce Python's startup CPU footprint
RUN python -m compileall -q /app/src/zabbix_mcp_server/ || true


ENV ZABBIX_MCP_TRANSPORT=streamable-http
ENV AUTH_TYPE=no-auth

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Run the server in HTTP mode
CMD ["python","scripts/start_server.py"]