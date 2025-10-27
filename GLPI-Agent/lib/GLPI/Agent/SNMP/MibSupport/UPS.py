"""
GLPI Agent SNMP MibSupport for UPS (APC, Riello)

This module enhances support for UPS devices (e.g., APC, Riello)
by collecting manufacturer, model, serial number, firmware version,
and type information via SNMP.

See:
- PowerNet-MIB
- UPS-MIB
"""

from typing import Optional, List, Dict, Any
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class UpsMibSupport(MibSupportTemplate):
    """
    Inventory module for UPS devices (APC, Riello)

    Provides SNMP-based inventory of UPS devices such as model, serial number,
    firmware version, and manufacturer.
    """

    # Enterprise OIDs
    APC = '.1.3.6.1.4.1.318'
    RIELLO = '.1.3.6.1.4.1.5491'

    # PowerNet-MIB (APC)
    UPS_ADV_IDENT_SERIAL_NUMBER = f'{APC}.1.1.1.1.2.3.0'
    SPDU_IDENT_FIRMWARE_REV = f'{APC}.1.1.4.1.2.0'
    SPDU_IDENT_MODEL_NUMBER = f'{APC}.1.1.4.1.4.0'
    SPDU_IDENT_SERIAL_NUMBER = f'{APC}.1.1.4.1.5.0'

    # UPS-MIB
    UPS_MIB = '.1.3.6.1.2.1.33'
    UPS_IDENT_MANUFACTURER = f'{UPS_MIB}.1.1.1.0'
    UPS_IDENT_MODEL = f'{UPS_MIB}.1.1.2.0'
    UPS_IDENT_UPS_SOFTWARE_VERSION = f'{UPS_MIB}.1.1.3.0'

    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for UPS devices
        """
        match = f"{cls.APC}|{cls.UPS_MIB}|{cls.RIELLO}"
        return [
            {
                "name": "apc",
                "sysobjectid": SNMPTools.get_regexp_oid_match(match)
            }
        ]

    def getModel(self) -> Optional[str]:
        """
        Retrieve the UPS model name
        """
        model = self.get(self.UPS_IDENT_MODEL) or self.get(self.SPDU_IDENT_MODEL_NUMBER)
        return Tools.get_canonical_string(model) if model else None

    def getSerial(self) -> Optional[str]:
        """
        Retrieve the UPS serial number
        """
        serial = self.get(self.UPS_ADV_IDENT_SERIAL_NUMBER) or self.get(self.SPDU_IDENT_SERIAL_NUMBER)
        return Tools.get_canonical_string(serial) if serial else None

    def getFirmware(self) -> Optional[str]:
        """
        Retrieve the UPS firmware version
        """
        firmware = self.get(self.UPS_IDENT_UPS_SOFTWARE_VERSION) or self.get(self.SPDU_IDENT_FIRMWARE_REV)
        return Tools.get_canonical_string(firmware) if firmware else None

    def getManufacturer(self) -> Optional[str]:
        """
        Retrieve the UPS manufacturer name
        """
        manufacturer = self.get(self.UPS_IDENT_MANUFACTURER)
        return Tools.get_canonical_string(manufacturer) if manufacturer else None

    def getType(self) -> str:
        """
        Returns the device type.
        TODO: Replace 'NETWORKING' with 'POWER' once supported server-side.
        """
        return 'NETWORKING'


# Module-level variable for backward compatibility
mib_support = UpsMibSupport.get_mib_support()

# Metadata
__all__ = ['UpsMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for UPS devices (APC, Riello)'
