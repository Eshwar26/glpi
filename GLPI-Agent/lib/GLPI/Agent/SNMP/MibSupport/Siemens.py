"""
GLPI Agent SNMP MibSupport for Siemens devices

This module provides inventory support for Siemens industrial modules via SNMP.
It extracts model, serial number, firmware, and other device information.
"""

import re
from typing import Optional, List, Dict, Any, Pattern
from glpi_agent.snmp.mib_support_template import MibSupportTemplate
from glpi_agent.tools import Tools
from glpi_agent.tools.snmp import SNMPTools


class SiemensMibSupport(MibSupportTemplate):
    """
    Inventory module for Siemens industrial modules
    
    This module enhances Siemens devices support by providing comprehensive
    device information retrieval including model, serial, firmware, and MAC address.
    Handles special cases where standard MIB support reports sysObjectID of ".0.0"
    """
    
    # Priority for this MIB support
    PRIORITY = 20
    
    # Standard MIB OIDs
    SYSDESCR = '.1.3.6.1.2.1.1.1.0'
    
    # Vendor-specific OIDs
    AD = '.1.3.6.1.4.1.4196'
    SIEMENS = '.1.3.6.1.4.1.4329'
    
    # iAsiLink MIB
    I_ASI_LINK_MIB = f'{AD}.1.1.8.3.100'
    SN_GEN = f'{I_ASI_LINK_MIB}.1.8'
    SN_TCP_IP = f'{I_ASI_LINK_MIB}.1.10'
    
    # General information OIDs
    SN_SW_VERSION = f'{SN_GEN}.4.0'
    SN_INFO_SERIAL_NR = f'{SN_GEN}.6.0'
    SN_INFO_MLFB_NR = f'{SN_GEN}.26.0'
    SN_MAC_ADDRESS_BASE = f'{SN_TCP_IP}.10.0'
    
    # Device name OID
    SN_ASI_LINK_PNIO_DEVICE_NAME = f'{I_ASI_LINK_MIB}.2.21.2.0'
    
    # Module information OIDs
    MODULE_MLFB = f'{SIEMENS}.6.3.2.1.1.2.0'
    MODULE_SERIAL = f'{SIEMENS}.6.3.2.1.1.3.0'
    MODULE_FIRMWARE = f'{SIEMENS}.6.3.2.1.1.5.0'
    
    # Model number lookup table
    MLFB_MODELS = {
        '6GK1 411-2AB10': 'IE/AS-i LINK PN IO',
        '6GK7 343-1CX10-0XE0': 'CP 343-1 Lean',
        '6ES7 318-3EL01-0AB0': 'CPU319-3 PN/DP',
    }
    
    @classmethod
    def get_mib_support(cls) -> List[Dict[str, Any]]:
        """
        Returns the MIB support configuration for Siemens devices
        
        Note: Standard MIB support for Siemens modules is sometimes bad,
        reporting a sysObjectID of ".0.0"
        
        Returns:
            List of dictionaries containing MIB support configuration
        """
        return [
            {
                'name': 'siemens',
                'sysobjectid': re.compile(r'^\.1\.3\.6\.1\.4\.1\.4196.*|\.0\.0$')
            }
        ]
    
    @classmethod
    def get_priority(cls) -> int:
        """
        Returns the priority level for this MIB support
        
        Returns:
            Priority value (higher values are processed first)
        """
        return cls.PRIORITY
    
    def get_type(self) -> str:
        """
        Returns the device type
        
        Returns:
            Device type string
        """
        return 'NETWORKING'
    
    def get_manufacturer(self) -> Optional[str]:
        """
        Retrieve the device manufacturer
        
        Returns:
            Manufacturer name or None if already set
        """
        device = self.device
        if not device:
            return None
        
        # Don't override if manufacturer is already set
        if device.get('MANUFACTURER'):
            return None
        
        return 'Siemens'
    
    def get_model(self) -> Optional[str]:
        """
        Retrieve the device model
        
        Returns:
            Model name or description string, or None if not available
        """
        # Try to get MLFB number from SNMP
        mlfb = Tools.get_canonical_string(
            self.get(self.SN_INFO_MLFB_NR) or self.get(self.MODULE_MLFB)
        )
        
        # If not found in SNMP, try to extract from sysDescr
        if not mlfb:
            sysdescr_parts = self._get_infos_from_descr()
            if len(sysdescr_parts) > 3:
                mlfb = sysdescr_parts[3]
        
        if not mlfb:
            return None
        
        # Look up friendly model name
        if mlfb in self.MLFB_MODELS:
            return self.MLFB_MODELS[mlfb]
        
        return f"Siemens module (PartNumber: {mlfb})"
    
    def _get_infos_from_descr(self, info_re: Optional[Pattern] = None) -> Any:
        """
        Extract information from sysDescr field
        
        Args:
            info_re: Optional regex pattern to match specific information
        
        Returns:
            If info_re is provided: matched string or empty string
            If info_re is None: list of sysDescr components
        """
        sysdescr = Tools.get_canonical_string(self.get(self.SYSDESCR))
        if not sysdescr:
            return '' if info_re else []
        
        sysdescr_parts = [part.strip() for part in sysdescr.split(',')]
        
        if info_re:
            # Find the first matching part
            for part in sysdescr_parts:
                match = info_re.search(part)
                if match:
                    return match.group(1) if match.groups() else match.group(0)
            return ''
        
        return sysdescr_parts
    
    def get_snmp_hostname(self) -> Optional[str]:
        """
        Retrieve the SNMP hostname
        
        Returns:
            Device name or serial number as fallback, or None
        """
        # Try to get device name
        name = Tools.get_canonical_string(
            self.get(self.SN_ASI_LINK_PNIO_DEVICE_NAME)
        )
        if name:
            return name
        
        # Fallback to serial number
        serial = self.get_serial()
        return serial if serial else None
    
    def get_serial(self) -> Optional[str]:
        """
        Retrieve the device serial number
        
        Returns:
            Serial number string or None if not available
        """
        # Try to get serial from SNMP
        serial = Tools.get_canonical_string(
            self.get(self.SN_INFO_SERIAL_NR) or self.get(self.MODULE_SERIAL)
        )
        
        # If not found in SNMP, try to extract from sysDescr
        if not serial:
            sysdescr_parts = self._get_infos_from_descr()
            if len(sysdescr_parts) > 6:
                serial = sysdescr_parts[6]
        
        # Check if serial is valid
        if serial and 'not set' not in serial.lower():
            return serial
        
        # Fallback to MAC address without colons
        mac = self.get_mac_address()
        if mac:
            serial = mac.replace(':', '')
            return serial
        
        return None
    
    def get_mac_address(self) -> Optional[str]:
        """
        Retrieve the device MAC address
        
        Returns:
            Canonical MAC address string or None if not available
        """
        return Tools.get_canonical_mac_address(
            self.get(self.SN_MAC_ADDRESS_BASE)
        )
    
    def get_firmware(self) -> Optional[str]:
        """
        Retrieve the device firmware version
        
        Returns:
            Firmware version string or None if not available
        """
        # Try to get firmware from SNMP
        version = Tools.get_canonical_string(
            self.get(self.SN_SW_VERSION) or self.get(self.MODULE_FIRMWARE)
        )
        
        # If not found in SNMP, try to extract from sysDescr
        if not version:
            version = self._get_infos_from_descr(re.compile(r'^FW:\s*(.*)$'))
        
        return version if version else None


# Module-level variable for backward compatibility
mib_support = SiemensMibSupport.get_mib_support()


# Module metadata
__all__ = ['SiemensMibSupport', 'mib_support']
__version__ = '1.0.0'
__author__ = 'GLPI Agent'
__description__ = 'Inventory module for Siemens industrial modules'
