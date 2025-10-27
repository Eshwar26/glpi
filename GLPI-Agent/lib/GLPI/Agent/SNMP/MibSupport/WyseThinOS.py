# GLPI/Agent/SNMP/MibSupport/WyseThinOS.py

from GLPI.Agent.SNMP.MibSupportTemplate import MibSupportTemplate
from GLPI.Agent.Tools.SNMP import getRegexpOidMatch


# SNMP OIDs (constants)
enterprises = '.1.3.6.1.4.1'
wyse = enterprises + '.714'
ThinClient = wyse + '.1.2'
SerialNumber = ThinClient + '.6.2.1.0'


# MIB Support registration
mibSupport = [
    {
        "name": "wyse-thinos",
        "sysobjectid": getRegexpOidMatch(ThinClient)
    }
]


class WyseThinOS(MibSupportTemplate):
    """Inventory module for Dell Wyse ThinClient devices (ThinOS)."""

    def getType(self):
        return "NETWORKING"

    def getModel(self):
        device = getattr(self, "device", None)
        if not device or "DESCRIPTION" not in device:
            return None

        description = device["DESCRIPTION"]
        parts = description.split(maxsplit=1)
        model = parts[0] if parts else None

        if model:
            return f"Wyse {model}"
        return None

    def getManufacturer(self):
        return "Dell"

    def getSerial(self):
        return self.get(SerialNumber)

    def run(self):
        device = getattr(self, "device", None)
        if not device or "DESCRIPTION" not in device:
            return

        description = device["DESCRIPTION"]
        parts = description.split(maxsplit=1)
        version = parts[1] if len(parts) > 1 else None

        if not version:
            return

        device.addFirmware({
            "NAME": "ThinOS",
            "DESCRIPTION": "Dell Wyse ThinOS",
            "TYPE": "system",
            "VERSION": version,
            "MANUFACTURER": "Dell"
        })


# Documentation equivalent to POD
"""
NAME
    GLPI.Agent.SNMP.MibSupport.WyseThinOS - Inventory module for Dell ThinClient

DESCRIPTION
    This module enhances Dell Wyse ThinClient support by gathering
    model, firmware, and serial number details through SNMP OIDs.
"""
