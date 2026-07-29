"""Auvik API constants and enum vocabularies.

All values come from the Auvik OpenAPI 3.0.1 spec and are used for
parameter validation and documentation in tool implementations.
"""

# --- Base URL ---

DEFAULT_BASE_URL = "https://auvikapi.us1.my.auvik.com"

# --- filter[interval] values ---

INTERVALS: set = {"minute", "hour", "day"}

# --- statId enumerations (per stat category) ---

DEVICE_STAT_IDS: set = {
    "bandwidth",
    "cpuUtilization",
    "memoryUtilization",
    "storageUtilization",
    "packetUnicast",
    "packetMulticast",
    "packetBroadcast",
}

DEVICE_AVAILABILITY_STAT_IDS: set = {"uptime", "outage"}

INTERFACE_STAT_IDS: set = {
    "bandwidth",
    "utilization",
    "packetLoss",
    "packetDiscard",
    "packetMulticast",
    "packetUnicast",
    "packetBroadcast",
}

SERVICE_STAT_IDS: set = {"pingTime", "pingPacket"}

COMPONENT_STAT_IDS: set = {
    "capacity",
    "counters",
    "idle",
    "latency",
    "power",
    "queueLatency",
    "rate",
    "readiness",
    "ready",
    "speed",
    "swap",
    "swapRate",
    "temperature",
    "totalLatency",
    "utilization",
}

# statId for OID poller (point-in-time)
OID_STAT_IDS: set = {"deviceMonitor"}

# --- componentType enum ---

COMPONENT_TYPES: set = {
    "cpu",
    "cpuCore",
    "disk",
    "fan",
    "memory",
    "powerSupply",
    "systemBoard",
}

# --- deviceType enum (48 values, verbatim from Auvik DeviceTypeSchema) ---

DEVICE_TYPES: set = {
    "unknown",
    "switch",
    "l3Switch",
    "router",
    "accessPoint",
    "firewall",
    "workstation",
    "server",
    "storage",
    "printer",
    "copier",
    "hypervisor",
    "multimedia",
    "phone",
    "tablet",
    "handheld",
    "virtualAppliance",
    "bridge",
    "controller",
    "hub",
    "modem",
    "ups",
    "module",
    "loadBalancer",
    "camera",
    "telecommunications",
    "packetProcessor",
    "chassis",
    "airConditioner",
    "virtualMachine",
    "pdu",
    "ipPhone",
    "backhaul",
    "internetOfThings",
    "voipSwitch",
    "stack",
    "backupDevice",
    "timeClock",
    "lightingDevice",
    "audioVisual",
    "securityAppliance",
    "utm",
    "alarm",
    "buildingManagement",
    "ipmi",
    "thinAccessPoint",
    "thinClient",
    "subnet",
}

# --- interfaceType enum (30 values, verbatim from Auvik filter[interfaceType]) ---

INTERFACE_TYPES: set = {
    "ethernet",
    "wifi",
    "bluetooth",
    "cdma",
    "coax",
    "cpu",
    "distributedVirtualSwitch",
    "firewire",
    "gsm",
    "ieee8023AdLag",
    "inferredWired",
    "inferredWireless",
    "interface",
    "linkAggregation",
    "loopback",
    "modem",
    "wimax",
    "optical",
    "other",
    "parallel",
    "ppp",
    "radiomac",
    "rs232",
    "tunnel",
    "unknown",
    "usb",
    "virtualBridge",
    "virtualNic",
    "virtualSwitch",
    "vlan",
}

# --- Alert enum values ---

ALERT_SEVERITIES: set = {"unknown", "emergency", "critical", "warning", "info"}

ALERT_STATUSES: set = {"created", "resolved", "paused", "unpaused"}

# --- Lifecycle status enum ---

LIFECYCLE_STATUSES: set = {
    "covered",
    "available",
    "expired",
    "securityOnly",
    "unpublished",
    "empty",
}

# --- onlineStatus enum ---

ONLINE_STATUSES: set = {
    "online",
    "offline",
    "unreachable",
    "testing",
    "unknown",
    "dormant",
    "notPresent",
    "lowerLayerDown",
}

# --- networkType enum ---

NETWORK_TYPES: set = {"routed", "vlan", "wifi", "loopback", "network", "layer2", "internet"}
