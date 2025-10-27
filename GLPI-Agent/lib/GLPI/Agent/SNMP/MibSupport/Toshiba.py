"""
GLPI Agent SNMP MibSupport for Toshiba devices

This module provides inventory support for Toshiba printers via SNMP.
It extracts model, serial number, firmware version, and boot software version.
"""

from typing import Optional, List, Dict, Any
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class ToshibaMibSupport(MibSupportTemplate):
    """
    Inventory module for Toshiba printers
    
    This module enhances Toshiba printers support by providing device information
    including model, serial number, firmware version, and boot software version.
    """
    
    # OID Constants - Toshiba TEC MIB
    TOSHIBATEC = '.1.3.6.1.4.1.1129'
    
    # BCP General Information
    BCP_GENERAL = f'{TOSHIBATEC}.1.2.1.1.1.1'
    BCP_PRODUCT_NUMBER = f'{BCP_GENERAL}.1.0'
    BCP_PRODUCT_VERSION = f'{BCP_GENERAL}.2.0'
    
    # BCP Device Entry
    BCP_DEVICE_ENTRY = f'{TOSHIBATEC}.1.2.1.1.1.2'
    BCP_DEVICE_MODEL = f'{BCP_DEVICE_ENTRY}.1.0'
    BCP_DEVICE_BOOT_VERSION = f'{BCP_DEVICE_ENTRY}.5.0'
    
    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for Toshiba devices
        
        Returns:
            List of dictionaries containing MIB support configuration
        """
        return [
            {
                'name': 'toshiba',
                'sysobjectid': SNMPTools.get_regexp_oid_match(cls.TOSHIBATEC)
            }
        ]
    
    def getSerial(self) -> Optional[str]:
        """
        Retrieve the device serial number
        
        Returns:
            Product number (serial) or None if not available
        """
        return Tools.get_canonical_string(self.get(self.BCP_PRODUCT_NUMBER))
    
    def getModel(self) -> Optional[str]:
        """
        Retrieve the device model
        
        Returns:
            Device model or None if not available
        """
        return Tools.get_canonical_string(self.get(self.BCP_DEVICE_MODEL))
    
    def run(self) -> None:
        """
        Execute additional inventory tasks
        
        Extracts and adds firmware information:
        - Main firmware version (with B->V prefix conversion)
        - Boot software version
        
        Both components are added as printer-type firmware entries.
        """
        device = self.device
        if not device:
            return
        
        # Process main firmware version
        version = Tools.get_canonical_string(self.get(self.BCP_PRODUCT_VERSION))
        if version:
            # Convert 'B' prefix to 'V' prefix (e.g., "B1.2.3" -> "V1.2.3")
            if version.startswith('B'):
                version = 'V' + version[1:]
            
            firmware = {
                'NAME': 'Toshiba firmware',
                'DESCRIPTION': 'Toshiba printer firmware',
                'TYPE': 'printer',
                'VERSION': version,
                'MANUFACTURER': 'Toshiba'
            }
            device.addFirmware(firmware)
        
        # Process boot software version
        bootversion = Tools.get_canonical_string(self.get(self.BCP_DEVICE_BOOT_VERSION))
        if bootversion:
            firmware = {
                'NAME': 'Toshiba boot software',
                'DESCRIPTION': 'Boot software version',
                'TYPE': 'printer',
                'VERSION': bootversion,
                'MANUFACTURER': 'Toshiba'
            }
            device.addFirmware(firmware)


# Module-level variable for backward compatibility
mib_support = ToshibaMibSupport.get_mib_support()


# Module metadata
__all__ = ['ToshibaMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for Toshiba printers'
