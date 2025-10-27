# GLPI/Agent/SNMP/MibSupport/Voltaire.py

from GLPI.Agent.SNMP.MibSupportTemplate import MibSupportTemplate
from GLPI.Agent.Tools import getCanonicalString
from GLPI.Agent.Tools.SNMP import getRegexpOidMatch


# SNMP OIDs
sysName = '.1.3.6.1.2.1.1.5.0'
enterprises = '.1.3.6.1.4.1'
voltaire = enterprises + '.5206'
serialnumber = voltaire + '.3.29.1.3.1007.1'
version = voltaire + '.3.1.0'


# MIB Support registration
mibSupport = [
    {
        "name": "voltaire",
        "sysobjectid": getRegexpOidMatch(voltaire)
    }
]


class Voltaire(MibSupportTemplate):
    """Inventory module for Voltaire devices."""

    def getType(self):
        return "NETWORKING"

    def getManufacturer(self):
        return "Voltaire"

    def getModel(self):
        sys_name = self.get(sysName)
        if not sys_name:
            return None

        # Extract model (text before '-')
        parts = sys_name.split('-', 1)
        model = parts[0] if parts else None
        return model

    def getSerial(self):
        return self.get(serialnumber)

    def getFirmware(self):
        return self.get(version)


# Documentation equivalent to POD
"""
NAME
    GLPI.Agent.SNMP.MibSupport.Voltaire - Inventory module for Voltaire devices

DESCRIPTION
    This module enhances Voltaire devices support by extracting model, serial,
    and firmware information from SNMP OIDs.
"""
