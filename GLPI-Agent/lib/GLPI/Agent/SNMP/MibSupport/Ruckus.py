"""
GLPI Agent SNMP MibSupport for Ruckus devices

This module provides inventory support for Ruckus devices via SNMP.
It extracts model, serial number, and firmware information using Ruckus MIBs.
"""

from typing import Optional, List, Dict, Any
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class RuckusMibSupport(MibSupportTemplate):
    """
    Inventory module for Ruckus devices
    
    This module enhances Ruckus devices support by providing
    model, serial number, and firmware information retrieval.
    """
    
    # OID Constants
    ENTERPRISES = '.1.3.6.1.4.1'
    
    # RUCKUS-ROOT-MIB
    RUCKUS_ROOT_MIB = f'{ENTERPRISES}.25053'
    RUCKUS_PRODUCTS = f'{RUCKUS_ROOT_MIB}.3'
    RUCKUS_COMMON_HW_INFO_MODULE = f'{RUCKUS_ROOT_MIB}.1.1.2'
    RUCKUS_COMMON_SW_INFO_MODULE = f'{RUCKUS_ROOT_MIB}.1.1.3'
    
    # RUCKUS-HWINFO-MIB
    RUCKUS_HW_INFO = f'{RUCKUS_COMMON_HW_INFO_MODULE}.1.1.1'
    RUCKUS_HW_INFO_MODEL_NUMBER = f'{RUCKUS_HW_INFO}.1.0'
    RUCKUS_HW_INFO_SERIAL_NUMBER = f'{RUCKUS_HW_INFO}.2.0'
    
    # RUCKUS-SWINFO-MIB
    RUCKUS_SW_INFO = f'{RUCKUS_COMMON_SW_INFO_MODULE}.1.1.1'
    RUCKUS_SW_REVISION = f'{RUCKUS_SW_INFO}.1.1.3.1'
    
    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for Ruckus devices
        
        Returns:
            List of dictionaries containing MIB support configuration
        """
        return [
            {
                'name': 'ruckus',
                'sysobjectid': SNMPTools.get_regexp_oid_match(cls.RUCKUS_PRODUCTS)
            }
        ]
    
    def get_model(self) -> Optional[str]:
        """
        Retrieve the device model number
        
        Returns:
            Model number string or None if not available
        """
        return self.get(self.RUCKUS_HW_INFO_MODEL_NUMBER)
    
    def get_serial(self) -> Optional[str]:
        """
        Retrieve the device serial number
        
        Returns:
            Serial number string or None if not available
        """
        return self.get(self.RUCKUS_HW_INFO_SERIAL_NUMBER)
    
    def get_firmware(self) -> Optional[str]:
        """
        Retrieve the device firmware version
        
        Returns:
            Firmware version string or None if not available
        """
        return self.get(self.RUCKUS_SW_REVISION)


# Module-level variable for backward compatibility
mib_support = RuckusMibSupport.get_mib_support()


# Module metadata
__all__ = ['RuckusMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for Ruckus devices'
