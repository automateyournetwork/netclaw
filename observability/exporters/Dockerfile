FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends snmp \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir prometheus_client pyyaml

WORKDIR /app
COPY bgp_snmp_exporter.py .

ENV BGP_SNMP_EXPORTER_PORT=9102
ENV BGP_SNMP_POLL_INTERVAL=60
EXPOSE 9102

CMD ["python3", "-u", "bgp_snmp_exporter.py"]