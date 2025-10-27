"""
GLPI Agent SNMP MibSupport for Snom devices

This module provides inventory support for Snom phones via SNMP.
It extracts model, firmware, and U-boot version information.

See: https://service.snom.com/display/wiki/How+to+setup+SNMP

Note: Snom phones don't support GET-NEXT-REQUEST, so SNMP walk is disabled.
"""

from typing import Optional, List, Dict, Any
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class SnomMibSupport(MibSupportTemplate):
    """
    Inventory module for Snom phones
    
    This module enhances Snom phones support by providing model, firmware,
    and U-boot version information. Special handling for devices that don't
    support SNMP walk operations.
    """
    
    # OID Constants
    # See https://service.snom.com/display/wiki/How+to+setup+SNMP
    SNOM = '.1.3.6.1.2.1.7526'
    FIRMWARE = f'{SNOM}.2.4'
    
    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for Snom devices
        
        Returns:
            List of dictionaries containing MIB support configuration
        """
        return [
            {
                'name': 'snom',
                'privateoid': cls.FIRMWARE
            }
        ]
    
    def __init__(self, **params):
        """
        Initialize Snom MIB support
        
        Disables SNMP walk support as Snom phones don't support GET-NEXT-REQUEST
        
        Args:
            **params: Parameters passed to parent constructor
        """
        super().__init__(**params)
        
        # Disable walk support in device as Snom phones don't support GET-NEXT-REQUEST
        if self.device:
            self.device.disable_walk()
    
    def get_type(self) -> str:
        """
        Returns the device type
        
        Returns:
            Device type string
        """
        return 'NETWORKING'
    
    def get_manufacturer(self) -> str:
        """
        Returns the device manufacturer
        
        Returns:
            Manufacturer name
        """
        return 'Snom'
    
    def get_model(self) -> Optional[str]:
        """
        Retrieve the device model
        
        Extracts the model from the firmware string (first component)
        Firmware format: "MODEL VERSION UBOOT"
        
        Returns:
            Model name or None if not available
        """
        firmware_string = Tools.get_canonical_string(self.get(self.FIRMWARE))
        if not firmware_string:
            return None
        
        # Firmware string format: "MODEL VERSION UBOOT"
        parts = firmware_string.split(None, 1)  # Split on whitespace, max 2 parts
        if parts:
            return parts[0]
        
        return None
    
    def get_firmware(self) -> Optional[str]:
        """
        Retrieve the device firmware version
        
        Extracts the firmware version from the firmware string (second component)
        Firmware format: "MODEL VERSION UBOOT"
        
        Returns:
            Firmware version or None if not available
        """
        firmware_string = Tools.get_canonical_string(self.get(self.FIRMWARE))
        if not firmware_string:
            return None
        
        # Firmware string format: "MODEL VERSION UBOOT"
        parts = firmware_string.split(None, 2)  # Split on whitespace, max 3 parts
        if len(parts) >= 2:
            return parts[1]
        
        return None
    
    def run(self) -> None:
        """
        Execute additional inventory tasks
        
        Extracts and adds U-boot firmware information if available.
        Firmware format: "MODEL VERSION UBOOT"
        """
        device = self.device
        if not device:
            return
        
        firmware_string = Tools.get_canonical_string(self.get(self.FIRMWARE))
        if not firmware_string:
            return
        
        # Firmware string format: "MODEL VERSION UBOOT"
        parts = firmware_string.split(None, 2)  # Split on whitespace, max 3 parts
        
        # Check if U-boot version exists (third component)
        if len(parts) < 3 or not parts[2] or Tools.is_empty(parts[2]):
            return
        
        uboot_version = parts[2]
        
        # Add U-boot firmware information to device
        device.add_firmware({
            'NAME': 'Snom Uboot version',
            'DESCRIPTION': 'Snom Uboot firmware',
            'TYPE': 'system',
            'VERSION': uboot_version,
            'MANUFACTURER': 'Snom'
        })


# Module-level variable for backward compatibility
mib_support = SnomMibSupport.get_mib_support()


# Module metadata
__all__ = ['SnomMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for Snom phones'
