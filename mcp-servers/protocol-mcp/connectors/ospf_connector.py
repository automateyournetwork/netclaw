"""
OSPF Connector

Connects agentic layer to OSPFv3 protocol implementation.
"""

from typing import Optional


class OSPFConnector:
    """
    Connector for OSPFv3 interface.

    Provides agentic layer access to OSPF state and actions.
    """

    def __init__(self, ospf_interface):
        """
        Initialize with OSPFv3 interface.

        Args:
            ospf_interface: Instance of OSPFv3Interface from wontyoubemyneighbor.ospfv3
        """
        self.interface = ospf_interface

    async def get_neighbors(self):
        """Get list of OSPF neighbors"""
        neighbors = []
        for neighbor in self.interface.neighbors.values():
            neighbors.append({
                "neighbor_id": neighbor.router_id,
                "state": neighbor.get_state_name(),
                "address": neighbor.ip_address,
                "priority": neighbor.priority
            })
        return neighbors

    async def get_lsdb(self):
        """Get OSPF Link State Database"""
        if not hasattr(self.interface, "lsdb"):
            return []

        lsas = []
        for lsa_key, lsa in self.interface.lsdb.items():
            lsas.append({
                "type": lsa.get("type"),
                "advertising_router": lsa.get("advertising_router"),
                "ls_id": lsa.get("ls_id"),
                "sequence": lsa.get("sequence", 0),
                "age": lsa.get("age", 0)
            })
        return lsas

    async def adjust_interface_cost(self, cost: int):
        """
        Adjust OSPF interface cost.

        This would modify the interface cost in the OSPF configuration.
        """
        if hasattr(self.interface, "cost"):
            old_cost = self.interface.cost
            self.interface.cost = cost
            return {
                "success": True,
                "old_cost": old_cost,
                "new_cost": cost
            }
        else:
            return {
                "success": False,
                "error": "Interface does not support cost adjustment"
            }

    def get_interface_info(self):
        """Get OSPF interface information"""
        return {
            "interface_name": getattr(self.interface, "interface", ""),
            "router_id": self.interface.router_id,
            "area_id": getattr(self.interface, "area_id", "0.0.0.0"),
            "state": getattr(self.interface, "state", "Unknown"),
            "cost": getattr(self.interface, "cost", 10),
            "hello_interval": getattr(self.interface, "hello_interval", 10),
            "dead_interval": getattr(self.interface, "dead_interval", 40)
        }
