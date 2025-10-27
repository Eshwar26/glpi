"""
GLPI Agent SNMP MibSupport for SonicWall devices

This module provides inventory support for SonicWall devices via SNMP.
It extracts model, serial number, ROM version, and SonicOS firmware information.
"""

from typing import Optional, List, Dict, Any
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class SonicWallMibSupport(MibSupportTemplate):
    """
    Inventory module for SonicWall devices
    
    This module enhances SonicWall devices support by providing model,
    serial number, ROM version, and SonicOS firmware information.
    """
    
    # OID Constants
    MIB2 = '.1.3.6.1.2.1'
    ENTERPRISES = '.1.3.6.1.4.1'
    
    # SonicWall MIB
    SONICWALL = f'{ENTERPRISES}.8741'
    
    # SonicWall System Information
    SNWL_SYS = f'{SONICWALL}.2.1.1'
    
    SNWL_SYS_MODEL = f'{SNWL_SYS}.1.0'
    SNWL_SYS_SERIAL_NUMBER = f'{SNWL_SYS}.2.0'
    SNWL_SYS_FIRMWARE_VERSION = f'{SNWL_SYS}.3.0'
    SNWL_SYS_ROM_VERSION = f'{SNWL_SYS}.4.0'
    
    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for SonicWall devices
        
        Returns:
            List of dictionaries containing MIB support configuration
        """
        return [
            {
                'name': 'sonicwall',
                'sysobjectid': SNMPTools.get_regexp_oid_match(cls.SONICWALL)
            }
        ]
    
    def getModel(self) -> Optional[str]:
        """
        Retrieve the device model
        
        Returns:
            Model name or None if not available
        """
        return self.get(self.SNWL_SYS_MODEL)
    
    def getSerial(self) -> Optional[str]:
        """
        Retrieve the device serial number
        
        Returns:
            Serial number or None if not available
        """
        return self.get(self.SNWL_SYS_SERIAL_NUMBER)
    
    def getFirmware(self) -> Optional[str]:
        """
        Retrieve the device ROM version
        
        Returns:
            ROM version or None if not available
        """
        return self.get(self.SNWL_SYS_ROM_VERSION)
    
    def run(self) -> None:
        """
        Execute additional inventory tasks
        
        Extracts and adds SonicOS firmware information to the device.
        Handles hex-encoded strings that need conversion.
        """
        device = self.device
        if not device:
            return
        
        # Get firmware version (may be hex-encoded)
        firmware_version_raw = self.get(self.SNWL_SYS_FIRMWARE_VERSION)
        if not firmware_version_raw:
            return
        
        # Convert hex to char and sanitize
        system_version = Tools.get_sanitized_string(
            Tools.hex2char(firmware_version_raw)
        )
        
        if not system_version:
            return
        
        # Get model name (may also be hex-encoded)
        model_raw = self.getModel()
        model_name = None
        if model_raw:
            model_name = Tools.get_sanitized_string(
                Tools.hex2char(model_raw)
            )
        
        # Add SonicOS firmware information to device
        device.addFirmware({
            'NAME': model_name,
            'DESCRIPTION': 'SonicOS firmware',
            'TYPE': 'system',
            'VERSION': system_version,
            'MANUFACTURER': 'SonicWall'
        })


# Module-level variable for backward compatibility
mib_support = SonicWallMibSupport.get_mib_support()


# Module metadata
__all__ = ['SonicWallMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for SonicWall devices'
