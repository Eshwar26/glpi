# -*- coding: utf-8 -*-
"""
GLPI.Agent.SNMP.MibSupport.Zyxel
Inventory module for Zyxel devices
"""

from GLPI.Agent.SNMP.MibSupportTemplate import MibSupportTemplate
from GLPI.Agent.Tools import getCanonicalString
from GLPI.Agent.Tools.SNMP import getRegexpOidMatch

class Zyxel(MibSupportTemplate):
    priority = 5

    # SNMP OIDs
    zyxel = '.1.3.6.1.4.1.890'
    products = zyxel + '.1'
    enterpriseSolution = products + '.15'
    esMgmt = enterpriseSolution + '.3'

    # ZYXEL-ES-COMMON MIB OIDs
    esSysInfo = esMgmt + '.1'
    sysSwVersionString = esSysInfo + '.6.0'
    sysProductModel = esSysInfo + '.11.0'
    sysProductSerialNumber = esSysInfo + '.12.0'

    mibSupport = [
        {
            "name": "zyxel",
            "sysobjectid": getRegexpOidMatch(enterpriseSolution)
        }
    ]

    def getFirmware(self):
        """Return firmware version string."""
        return getCanonicalString(self.get(self.sysSwVersionString))

    def getSerial(self):
        """Return device serial number."""
        return getCanonicalString(self.get(self.sysProductSerialNumber))

    def getManufacturer(self):
        """Return manufacturer name."""
        return "Zyxel"

    def getModel(self):
        """Return product model string."""
        return getCanonicalString(self.get(self.sysProductModel))


# --- Module Metadata ---
"""
NAME
    GLPI.Agent.SNMP.MibSupport.Zyxel - Inventory module for Zyxel devices

DESCRIPTION
    Enhances SNMP-based inventory collection for Zyxel devices.
"""
