# netgear_mib.py
from typing import Optional, Dict, Any, List

from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, glpi_version, walk

# Netgear MIB constants
NETGEAR = '.1.3.6.1.4.1.4526'

# NETGEAR-INVENTORY-MIB
FASTPATH_INVENTORY = NETGEAR + '.10.13'
AGENT_INVENTORY_UNIT_ENTRY = FASTPATH_INVENTORY + '.2.2.1'
AGENT_INVENTORY_UNIT_STATUS = AGENT_INVENTORY_UNIT_ENTRY + '.11'
AGENT_INVENTORY_UNIT_SERIAL_NUMBER = AGENT_INVENTORY_UNIT_ENTRY + '.19'

# NG700-INVENTORY-MIB
FASTPATH_INVENTORY2 = NETGEAR + '.11.13'
AGENT_INVENTORY_UNIT_ENTRY2 = FASTPATH_INVENTORY2 + '.2.2.1'
AGENT_INVENTORY_UNIT_STATUS2 = AGENT_INVENTORY_UNIT_ENTRY2 + '.11'
AGENT_INVENTORY_UNIT_SERIAL_NUMBER2 = AGENT_INVENTORY_UNIT_ENTRY2 + '.19'


class Netgear(MibSupportTemplate):
    mib_support = [
        {"name": "netgear-ng7000", "oid": FASTPATH_INVENTORY},
        {"name": "netgear-ng700", "oid": FASTPATH_INVENTORY2},
    ]

    def run(self) -> None:
        device: Optional[Dict[str, Any]] = self.device
        if not device:
            return

        components: Optional[Dict[str, Any]] = device.get("COMPONENTS")
        if not components or not isinstance(components.get("COMPONENT"), list):
            return

        # Identify chassis components
        chassis: List[Dict[str, Any]] = [
            comp for comp in components["COMPONENT"]
            if comp.get("TYPE") == "chassis"
        ]
        if len(chassis) <= 1:
            return

        status: Dict[Any, Any] = self.walk(AGENT_INVENTORY_UNIT_STATUS) or self.walk(AGENT_INVENTORY_UNIT_STATUS2) or {}
        serials: Dict[Any, Any] = self.walk(AGENT_INVENTORY_UNIT_SERIAL_NUMBER) or self.walk(AGENT_INVENTORY_UNIT_SERIAL_NUMBER2) or {}

        for ch in chassis:
            name = ch.get("NAME")
            if not name or not name.startswith("Unit "):
                continue

            unit = name.split("Unit ")[1]
            if not status.get(unit) or status[unit] != '1':
                continue
            if not serials.get(unit):
                continue

            ch["SERIAL"] = get_canonical_string(serials[unit])

            # GLPI >= 10.0.19 stack number support
            glpi_ver = glpi_version(device.get("glpi")) if device.get("glpi") else 0
            if not glpi_ver or glpi_ver >= glpi_version("10.0.19"):
                ch["STACK_NUMBER"] = unit
