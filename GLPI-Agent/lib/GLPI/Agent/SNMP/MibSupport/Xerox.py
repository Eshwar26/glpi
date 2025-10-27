# GLPI/Agent/SNMP/MibSupport/Xerox.py

from GLPI.Agent.SNMP.MibSupportTemplate import MibSupportTemplate
from GLPI.Agent.Tools.SNMP import getRegexpOidMatch


# SNMP OID constants
enterprises = '.1.3.6.1.4.1'
xerox = enterprises + '.253'
xeroxCommonMIB = xerox + '.8'

# XEROX-HOST-RESOURCES-EXT-MIB
xcmHrDevDetailEntry = xeroxCommonMIB + '.53.13.2.1'

xeroxTotalPrint = xcmHrDevDetailEntry + '.6.1.20.1'
xeroxColorPrint = xcmHrDevDetailEntry + '.6.1.20.33'
xeroxBlackPrint = xcmHrDevDetailEntry + '.6.1.20.34'
xeroxColorCopy = xcmHrDevDetailEntry + '.6.11.20.25'
xeroxBlackCopy = xcmHrDevDetailEntry + '.6.11.20.3'
xeroxScanSentByEmail = xcmHrDevDetailEntry + '.6.10.20.11'
xeroxScanSavedOnNetwork = xcmHrDevDetailEntry + '.6.10.20.12'


# MIB Support registration
mibSupport = [
    {
        "name": "xerox-printer",
        "sysobjectid": getRegexpOidMatch(xeroxCommonMIB)
    }
]


class Xerox(MibSupportTemplate):
    """Inventory module for Xerox printers (extended SNMP MIB support)."""

    def run(self):
        device = getattr(self, "device", None)
        if not device:
            return

        mapping = {
            "PRINTCOLOR": xeroxColorPrint,
            "PRINTBLACK": xeroxBlackPrint,
            "PRINTTOTAL": xeroxTotalPrint,
            "COPYCOLOR": xeroxColorCopy,
            "COPYBLACK": xeroxBlackCopy,
            "SCANNED": [
                xeroxScanSentByEmail,
                xeroxScanSavedOnNetwork,
            ]
        }

        device.setdefault("PAGECOUNTERS", {})

        for counter, oid in sorted(mapping.items()):
            count = 0

            # Handle multiple OIDs (e.g., for SCANNED)
            if isinstance(oid, list):
                for o in oid:
                    val = self.get(o)
                    count += int(val) if val and str(val).isdigit() else 0
            else:
                val = self.get(oid)
                if val and str(val).isdigit():
                    count = int(val)

            # Skip invalid or zero counts
            if not count:
                continue

            device["PAGECOUNTERS"][counter] = count

        # Define COPYTOTAL if partial counts exist
        copy_color = device["PAGECOUNTERS"].get("COPYCOLOR", 0)
        copy_black = device["PAGECOUNTERS"].get("COPYBLACK", 0)
        if copy_color or copy_black:
            device["PAGECOUNTERS"]["COPYTOTAL"] = copy_color + copy_black


# Documentation equivalent to POD
"""
NAME
    GLPI.Agent.SNMP.MibSupport.Xerox - Inventory module for Xerox Printers

DESCRIPTION
    This module enhances Xerox printer support by retrieving print, copy,
    and scan page counters from SNMP OIDs, and aggregates the total copy count.
"""
