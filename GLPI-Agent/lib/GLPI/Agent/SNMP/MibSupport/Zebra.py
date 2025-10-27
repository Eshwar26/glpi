# GLPI/Agent/SNMP/MibSupport/Zebra.py

from GLPI.Agent.SNMP.MibSupportTemplate import MibSupportTemplate
from GLPI.Agent.Tools import getCanonicalString, hex2char, empty
from GLPI.Agent.Tools.SNMP import getRegexpOidMatch


# Priority for SNMP discovery order
priority = 7

# --- SNMP OID constants ---

# ESI-MIB
esi = '.1.3.6.1.4.1.683'
model2 = esi + '.6.2.3.2.1.15.1'
serial = esi + '.1.5.0'
fw2 = esi + '.1.9.0'

# ZEBRA-MIB
zebra = '.1.3.6.1.4.1.10642'
zbrGeneralInfo = zebra + '.1'

zbrGeneralModel = zbrGeneralInfo + '.1'
zbrGeneralFirmwareVersion = zbrGeneralInfo + '.2.0'
zbrGeneralName = zbrGeneralInfo + '.4.0'
zbrGeneralUniqueId = zbrGeneralInfo + '.9.0'
zbrGeneralCompanyName = zbrGeneralInfo + '.11.0'
zbrGeneralLINKOSVersion = zbrGeneralInfo + '.18.0'

# ZEBRA-QL-MIB
model1 = zbrGeneralModel + '.0'
zql_zebra_ql = zebra + '.200'
model3 = zql_zebra_ql + '.19.7.0'
serial3 = zql_zebra_ql + '.19.5.0'


# --- MIB Support registration ---
mibSupport = [
    {
        "name": "zebra-printer",
        "sysobjectid": getRegexpOidMatch(esi)
    },
    {
        "name": "zebra-printer-zt",
        "sysobjectid": getRegexpOidMatch(zbrGeneralModel)
    }
]


class Zebra(MibSupportTemplate):
    """Inventory module for Zebra printers (enhanced SNMP support)."""

    def getSnmpHostname(self):
        """Retrieve the SNMP hostname of the device."""
        val = self.get(zbrGeneralName)
        return getCanonicalString(val)

    def getManufacturer(self):
        """Retrieve manufacturer name."""
        val = self.get(zbrGeneralCompanyName)
        return getCanonicalString(val) or "Zebra Technologies"

    def getSerial(self):
        """Retrieve device serial number (prefers zbrGeneralUniqueId or serial3)."""
        val = (
            self.get(zbrGeneralUniqueId)
            or self.get(serial3)
            or self.get(serial)
        )
        return getCanonicalString(val) or hex2char(val)

    def getModel(self):
        """Retrieve model name from several possible OIDs."""
        val = self.get(model1) or self.get(model2) or self.get(model3)
        return hex2char(val)

    def getFirmware(self):
        """Retrieve firmware version."""
        val = self.get(zbrGeneralFirmwareVersion) or self.get(fw2)
        return hex2char(val)

    def run(self):
        """Add firmware details (LinkOS) to the device record."""
        device = getattr(self, "device", None)
        if not device:
            return

        manufacturer = self.getManufacturer()
        if not manufacturer:
            return

        linkos_version = self.get(zbrGeneralLINKOSVersion)
        if empty(linkos_version):
            return

        device.addFirmware({
            "NAME": f"{manufacturer} LinkOS",
            "DESCRIPTION": f"{manufacturer} LinkOS firmware",
            "TYPE": "system",
            "VERSION": getCanonicalString(linkos_version),
            "MANUFACTURER": manufacturer
        })


# --- Documentation equivalent to POD ---
"""
NAME
    GLPI.Agent.SNMP.MibSupport.Zebra - Inventory module for Zebra Printers

DESCRIPTION
    This module enhances Zebra printer support by gathering hostname, model,
    serial, and firmware details using SNMP MIBs (ESI-MIB, ZEBRA-MIB, ZEBRA-QL-MIB),
    and adds LinkOS firmware information for compatible devices.
"""
