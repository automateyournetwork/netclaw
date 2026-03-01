"""Connector adapters between protocol modules and MCP tools."""
from .bgp_connector import BGPConnector
from .ospf_connector import OSPFConnector

__all__ = ["BGPConnector", "OSPFConnector"]
