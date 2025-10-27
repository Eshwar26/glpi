"""
GLPI Agent SNMP MibSupport for Sophos devices

This module provides inventory support for Sophos UTM/XG Firewall devices via SNMP.
It extracts device information and integrated component versions (webcat, snort).

See: SFOS-FIREWALL-MIB
"""

from typing import Optional, List, Dict, Any
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class SophosMibSupport(MibSupportTemplate):
    """
    Inventory module for Sophos UTM/XG Firewall devices
    
    This module enhances Sophos devices support by providing device information
    and integrated component versions including webcat and snort IPS.
    """
    
    # OID Constants - SFOS-FIREWALL-MIB
    SOPHOS_MIB = '.1.3.6.1.4.1.2604'
    SFOS_XG_MIB = f'{SOPHOS_MIB}.5'
    SFOS_XG_DEVICE_INFO = f'{SFOS_XG_MIB}.1.1'
    
    # Device Information OIDs
    SFOS_DEVICE_NAME = f'{SFOS_XG_DEVICE_INFO}.1.0'
    SFOS_DEVICE_TYPE = f'{SFOS_XG_DEVICE_INFO}.2.0'
    SFOS_DEVICE_FW_VERSION = f'{SFOS_XG_DEVICE_INFO}.3.0'
    SFOS_WEBCAT_VERSION = f'{SFOS_XG_DEVICE_INFO}.5.0'
    SFOS_IPS_VERSION = f'{SFOS_XG_DEVICE_INFO}.6.0'
    
    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for Sophos devices
        
        Returns:
            List of dictionaries containing MIB support configuration
        """
        return [
            {
                'name': 'sophos',
                'sysobjectid': cls.SFOS_XG_MIB
            }
        ]
    
    def getModel(self) -> Optional[str]:
        """
        Retrieve the device model/type
        
        Returns:
            Device type/model or None if not available
        """
        return Tools.get_canonical_string(self.get(self.SFOS_DEVICE_TYPE))
    
    def getFirmware(self) -> Optional[str]:
        """
        Retrieve the device firmware version
        
        Returns:
            Firmware version or None if not available
        """
        return Tools.get_canonical_string(self.get(self.SFOS_DEVICE_FW_VERSION))
    
    def getSerial(self) -> Optional[str]:
        """
        Retrieve the device serial number/name
        
        Note: Uses device name as serial identifier
        
        Returns:
            Device name or None if not available
        """
        return Tools.get_canonical_string(self.get(self.SFOS_DEVICE_NAME))
    
    def run(self) -> None:
        """
        Execute additional inventory tasks
        
        Extracts and adds integrated component versions:
        - Webcat (web content filtering)
        - Snort (IPS/intrusion prevention system)
        
        Components are only added if available and not marked as "Not available"
        """
        device = self.device
        if not device:
            return
        
        # Process Webcat version
        webcat = Tools.get_canonical_string(self.get(self.SFOS_WEBCAT_VERSION))
        if webcat and not self._is_not_available(webcat):
            # Add webcat firmware
            webcat_firmware = {
                'NAME': 'webcat',
                'DESCRIPTION': 'Integrated webcat version',
                'TYPE': 'software',
                'VERSION': webcat,
                'MANUFACTURER': 'Sophos'
            }
            device.addFirmware(webcat_firmware)
        
        # Process Snort IPS version
        snort = Tools.get_canonical_string(self.get(self.SFOS_IPS_VERSION))
        if snort and not self._is_not_available(snort):
            # Add snort firmware
            snort_firmware = {
                'NAME': 'snort',
                'DESCRIPTION': 'Integrated snort version',
                'TYPE': 'software',
                'VERSION': snort,
                'MANUFACTURER': 'Sophos'
            }
            device.addFirmware(snort_firmware)
    
    def _is_not_available(self, value: str) -> bool:
        """
        Check if a version string indicates unavailability
        
        Args:
            value: Version string to check
        
        Returns:
            True if value contains "Not available" (case-insensitive)
        """
        if not value:
            return True
        return 'not available' in value.lower()


# Module-level variable for backward compatibility
mib_support = SophosMibSupport.get_mib_support()


# Module metadata
__all__ = ['SophosMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for Sophos UTM/XG Firewall devices'
