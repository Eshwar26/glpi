"""
GLPI Agent SNMP MIB Support Template Module

This module provides the base/template class for MIB-specific support modules.
It is a Python conversion of the Perl GLPI::Agent::SNMP::MibSupportTemplate module.

MIB Support modules extend this base class to provide device-specific functionality
for extracting information from network devices using their proprietary MIBs.

The module supports:
- Device-specific information extraction methods
- MIB matching by sysObjectID patterns
- MIB matching by sysORID entries
- Priority-based module selection
- SNMP GET and WALK operations through device proxy
- Component and firmware inventory collection

Author: Converted from Perl to Python
License: Compatible with GLPI Agent
"""

import re
from typing import Optional, Dict, List, Any, Pattern
from abc import ABC, ABCMeta


class MibSupportTemplate:
    """
    Base class for MIB Support modules.
    
    This template class provides the foundation for device-specific MIB support
    implementations. Subclasses should override the relevant methods to provide
    device-specific information extraction.
    
    The class provides:
    - Access to the SNMP device object
    - Convenience methods for SNMP operations
    - Template methods for standard device information extraction
    - Support for firmware and component inventory
    
    Attributes:
        _device: Reference to the SNMP device object
        _mibsupport: Reference to the parent MibSupport manager
        
    Class Attributes:
        priority: Priority for this MIB support module (lower = higher priority)
        enterprises: Base OID for enterprise-specific MIBs
        mib_support: List of dictionaries defining MIB support matching criteria
    """
    
    # Default priority to permit prioritizing one MibSupport module over another
    # A lower priority means use it before others
    priority = 10
    
    # Define here constants as defined in related MIB
    enterprises = '.1.3.6.1.4.1'
    
    # Example constants (commented out - define in subclasses)
    # section_oid = enterprises + '.XYZ'
    # value_oid = section_oid + '.xyz.abc'
    # mib_oid = section_oid + '.x.y.z'
    
    # MIB support matching criteria
    # Subclasses should define this list with their specific matching rules
    mib_support = [
        # Examples of MIB support by sysObjectID matching:
        # {
        #     'name': 'mibName',
        #     'sysobjectid': re.compile(r'^\.1\.3\.6\.1\.4\.1\.ENTERPRISE\.X\.Y')
        # },
        # {
        #     'name': 'mibName',
        #     'sysobjectid': get_regexp_oid_match(enterprises + '.ENTERPRISE.X.Y')
        # },
        
        # Example of MIB support by checking SNMP agent exposed MIB support
        # via sysORID entries:
        # {
        #     'name': 'mibName',
        #     'oid': mib_oid
        # }
    ]
    
    def __init__(self, device=None, mibsupport=None, **params):
        """
        Initialize the MIB Support module.
        
        Args:
            device: The SNMP device object (mandatory)
            mibsupport: Reference to the parent MibSupport manager
            **params: Additional parameters
            
        Raises:
            ValueError: If device parameter is not provided
        """
        if not device:
            raise ValueError("device parameter is required")
        
        self._device = device
        self._mibsupport = mibsupport
    
    def device(self):
        """
        Get the SNMP device object.
        
        Returns:
            The SNMP device object associated with this MIB support instance
        """
        return self._device
    
    def support(self):
        """
        Get the parent MibSupport manager.
        
        Returns:
            The MibSupport manager object that loaded this module
        """
        return self._mibsupport
    
    def get(self, oid: str) -> Optional[Any]:
        """
        Perform SNMP GET operation on a single OID.
        
        This is a convenience wrapper around the device's get() method.
        
        Args:
            oid: The OID string to query
            
        Returns:
            The value retrieved from the device, or None if failed
        """
        if self._device:
            return self._device.get(oid)
        return None
    
    def walk(self, oid: str) -> Optional[Dict[str, Any]]:
        """
        Perform SNMP WALK operation on an OID tree.
        
        This is a convenience wrapper around the device's walk() method.
        
        Args:
            oid: The base OID to walk
            
        Returns:
            Dictionary of OID suffixes to values, or None if failed
        """
        if self._device:
            return self._device.walk(oid)
        return None
    
    def get_sequence(self, oid: str) -> Optional[List[Any]]:
        """
        Get values from an OID tree as an ordered sequence.
        
        This method walks an OID tree and returns the values in numeric
        order of their OID suffixes. Useful for SNMP tables where you
        need values in index order.
        
        Args:
            oid: The base OID to walk
            
        Returns:
            List of values in OID suffix order, or None if no values found
            
        Example:
            If walk returns {'1': 'a', '10': 'b', '2': 'c'}
            This returns ['a', 'c', 'b'] (sorted by numeric index: 1, 2, 10)
        """
        if not self._device:
            return None
        
        walk_result = self._device.walk(oid)
        if not walk_result:
            return None
        
        # Sort keys numerically and return values in order
        try:
            sorted_keys = sorted(walk_result.keys(), key=lambda x: int(x.split('.')[0]))
        except (ValueError, AttributeError):
            # Fallback to string sorting if numeric conversion fails
            sorted_keys = sorted(walk_result.keys())
        
        return [walk_result[key] for key in sorted_keys]
    
    # =========================================================================
    # Device Information Extraction Methods
    # =========================================================================
    # The following methods should be overridden in subclasses to provide
    # device-specific information extraction. They return None by default.
    # =========================================================================
    
    def get_firmware(self) -> Optional[str]:
        """
        Get the device firmware version.
        
        Override this method in subclasses to extract firmware version
        from device-specific MIB OIDs.
        
        Returns:
            Firmware version string, or None if not available
            
        Example implementation:
            def get_firmware(self):
                return self.get(self.section_oid + '.X.A')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.A')
    
    def get_firmware_date(self) -> Optional[str]:
        """
        Get the device firmware date/timestamp.
        
        Override this method in subclasses to extract firmware date
        from device-specific MIB OIDs.
        
        Returns:
            Firmware date string, or None if not available
            
        Example implementation:
            def get_firmware_date(self):
                return self.get(self.section_oid + '.X.B')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.B')
    
    def get_serial(self) -> Optional[str]:
        """
        Get the device serial number.
        
        Override this method in subclasses to extract serial number
        from device-specific MIB OIDs.
        
        Returns:
            Serial number string, or None if not available
            
        Example implementation:
            def get_serial(self):
                return self.get(self.section_oid + '.X.C')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.C')
    
    def get_mac_address(self) -> Optional[str]:
        """
        Get the device MAC address.
        
        Override this method in subclasses to extract MAC address
        from device-specific MIB OIDs.
        
        Returns:
            MAC address string, or None if not available
            
        Example implementation:
            def get_mac_address(self):
                return self.get(self.section_oid + '.X.D')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.D')
    
    def get_ip(self) -> Optional[str]:
        """
        Get the device IP address.
        
        Override this method in subclasses to extract IP address
        from device-specific MIB OIDs.
        
        Returns:
            IP address string, or None if not available
            
        Example implementation:
            def get_ip(self):
                return self.get(self.section_oid + '.X.E')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.E')
    
    def get_model(self) -> Optional[str]:
        """
        Get the device model name.
        
        Override this method in subclasses to extract model name
        from device-specific MIB OIDs.
        
        Returns:
            Model name string, or None if not available
            
        Example implementation:
            def get_model(self):
                return self.get(self.section_oid + '.X.F')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.F')
    
    def get_type(self) -> Optional[str]:
        """
        Get the device type.
        
        Override this method in subclasses to determine device type
        from device-specific MIB OIDs or values.
        
        Returns:
            Device type string (e.g., 'NETWORKING', 'PRINTER', 'POWER'),
            or None if not determinable
            
        Example implementation:
            def get_type(self):
                value = self.get(self.section_oid + '.X.G')
                if value == 'XYZ':
                    return 'NETWORKING'
                return None
        """
        return None
        # Example:
        # value = self.get(section_oid + '.X.G')
        # return 'NETWORKING' if value == 'XYZ' else None
    
    def get_snmp_hostname(self) -> Optional[str]:
        """
        Get the device SNMP hostname.
        
        Override this method in subclasses to extract hostname
        from device-specific MIB OIDs.
        
        Returns:
            Hostname string, or None if not available
            
        Example implementation:
            def get_snmp_hostname(self):
                return self.get(self.section_oid + '.X.H')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.H')
    
    def get_manufacturer(self) -> Optional[str]:
        """
        Get the device manufacturer name.
        
        Override this method in subclasses to extract manufacturer
        from device-specific MIB OIDs.
        
        Returns:
            Manufacturer name string, or None if not available
            
        Example implementation:
            def get_manufacturer(self):
                return self.get(self.section_oid + '.X.I')
        """
        return None
        # Example:
        # return self.get(section_oid + '.X.I')
    
    def get_components(self) -> List[Dict[str, Any]]:
        """
        Get device hardware components.
        
        Override this method in subclasses to extract component information
        from device-specific MIB OIDs. Components include items like power
        supplies, fans, modules, etc.
        
        Returns:
            List of component dictionaries, each containing:
            - NAME: Component name
            - TYPE: Component type
            - MODEL: Component model
            - SERIAL: Component serial number
            - etc.
            Empty list if no components found
            
        Example implementation:
            def get_components(self):
                components = []
                power_supplies = self.walk(self.section_oid + '.psu')
                for index, status in power_supplies.items():
                    component = {
                        'NAME': f'PSU {index}',
                        'TYPE': 'POWER_SUPPLY',
                        'STATUS': status
                    }
                    components.append(component)
                return components
        """
        return []
        # Example:
        # return []
    
    def run(self):
        """
        Execute device-specific inventory collection.
        
        Override this method in subclasses to perform custom inventory
        operations. This is called during the inventory process and can
        add firmwares, modems, components, or other device-specific data.
        
        Example implementation:
            def run(self):
                device = self.device()
                if not device:
                    return
                
                # Add additional firmware information
                other_firmware = {
                    'NAME': 'XXX Device',
                    'DESCRIPTION': 'XXX ' + self.get(self.section_oid + '.X.D') + ' device',
                    'TYPE': 'Device type',
                    'VERSION': self.get(self.section_oid + '.X.D'),
                    'MANUFACTURER': 'XXX'
                }
                device.add_firmware(other_firmware)
        """
        pass
        # Example:
        # device = self.device()
        # if not device:
        #     return
        # 
        # other_firmware = {
        #     'NAME': 'XXX Device',
        #     'DESCRIPTION': 'XXX ' + self.get(section_oid + '.X.D') + ' device',
        #     'TYPE': 'Device type',
        #     'VERSION': self.get(section_oid + '.X.D'),
        #     'MANUFACTURER': 'XXX'
        # }
        # device.add_firmware(other_firmware)
    
    def configure(self, config: Optional[Dict[str, Any]] = None):
        """
        Configure the MIB support module.
        
        Use this method for module initialization. It is called when the
        module is loaded and can be used to set up internal state, validate
        configuration, or perform one-time setup operations.
        
        Args:
            config: Configuration dictionary (optional)
            
        Example implementation:
            def configure(self, config=None):
                if config:
                    self.timeout = config.get('timeout', 30)
                    self.retries = config.get('retries', 3)
        """
        pass


# ============================================================================= 
# Utility Functions
# =============================================================================

def get_regexp_oid_match(oid: str) -> Pattern:
    """
    Create a compiled regex pattern for matching OIDs.
    
    This helper function creates a regex pattern that matches OIDs starting
    with the specified prefix. It escapes dots and adds anchors for exact
    matching.
    
    Args:
        oid: The OID prefix to match (e.g., '.1.3.6.1.4.1.9.1')
        
    Returns:
        Compiled regex pattern that matches the OID prefix
        
    Example:
        pattern = get_regexp_oid_match('.1.3.6.1.4.1.9.1')
        # Matches OIDs like '.1.3.6.1.4.1.9.1.123', '.1.3.6.1.4.1.9.1.456', etc.
    """
    # Escape dots in OID for regex
    escaped_oid = oid.replace('.', r'\.')
    # Create pattern that matches OID prefix
    return re.compile(f'^{escaped_oid}')


# =============================================================================
# Example Subclass Implementation
# =============================================================================

class ExampleMibSupport(MibSupportTemplate):
    """
    Example MIB support implementation.
    
    This demonstrates how to create a concrete MIB support class by
    extending MibSupportTemplate.
    """
    
    # Set module priority (lower = higher priority)
    priority = 5
    
    # Define device-specific OID constants
    vendor_oid = MibSupportTemplate.enterprises + '.12345'
    system_oid = vendor_oid + '.1.1'
    device_info_oid = vendor_oid + '.1.2'
    
    # Define MIB support matching criteria
    mib_support = [
        {
            'name': 'ExampleVendor',
            'sysobjectid': re.compile(r'^\.1\.3\.6\.1\.4\.1\.12345\.1\.'),
        },
        {
            'name': 'ExampleVendor-Alt',
            'oid': vendor_oid + '.1.0',
        }
    ]
    
    def get_serial(self) -> Optional[str]:
        """Get device serial number from vendor-specific OID."""
        return self.get(self.device_info_oid + '.1.0')
    
    def get_firmware(self) -> Optional[str]:
        """Get firmware version from vendor-specific OID."""
        return self.get(self.device_info_oid + '.2.0')
    
    def get_model(self) -> Optional[str]:
        """Get device model from vendor-specific OID."""
        return self.get(self.device_info_oid + '.3.0')
    
    def get_type(self) -> Optional[str]:
        """Determine device type based on vendor-specific value."""
        device_type_value = self.get(self.device_info_oid + '.4.0')
        
        type_mapping = {
            '1': 'NETWORKING',
            '2': 'PRINTER',
            '3': 'POWER',
        }
        
        return type_mapping.get(device_type_value)
    
    def run(self):
        """Custom inventory collection for this vendor."""
        device = self.device()
        if not device:
            return
        
        # Add vendor-specific firmware information
        bootloader_version = self.get(self.device_info_oid + '.5.0')
        if bootloader_version:
            bootloader_firmware = {
                'NAME': 'Bootloader',
                'DESCRIPTION': 'Device bootloader firmware',
                'TYPE': 'BOOTLOADER',
                'VERSION': bootloader_version,
                'MANUFACTURER': 'Example Vendor'
            }
            device.add_firmware(bootloader_firmware)


# =============================================================================
# Module Usage Example
# =============================================================================

if __name__ == "__main__":
    """
    Example demonstrating how to use and extend MibSupportTemplate.
    """
    
    print("GLPI Agent SNMP MIB Support Template - Python Implementation")
    print("=" * 70)
    
    print("\nThis is a base class for creating MIB-specific support modules.")
    print("\nTo create a new MIB support module:")
    print("1. Extend MibSupportTemplate")
    print("2. Define priority and OID constants")
    print("3. Define mib_support matching criteria")
    print("4. Override relevant get_* methods")
    print("5. Implement run() for custom inventory")
    
    print("\n" + "-" * 70)
    print("Example MIB Support Module Structure:")
    print("-" * 70)
    
    print("""
class MyVendorMibSupport(MibSupportTemplate):
    # Lower priority = higher preference
    priority = 5
    
    # Define vendor OIDs
    vendor_oid = MibSupportTemplate.enterprises + '.9999'
    device_oid = vendor_oid + '.1.1'
    
    # Match devices by sysObjectID
    mib_support = [
        {
            'name': 'MyVendor',
            'sysobjectid': re.compile(r'^\\.1\\.3\\.6\\.1\\.4\\.1\\.9999\\.'),
        }
    ]
    
    def get_serial(self):
        return self.get(self.device_oid + '.1.0')
    
    def get_firmware(self):
        return self.get(self.device_oid + '.2.0')
    
    def get_model(self):
        return self.get(self.device_oid + '.3.0')
    
    def get_type(self):
        return 'NETWORKING'
    
    def run(self):
        device = self.device()
        if not device:
            return
        
        # Add custom firmware
        firmware = {
            'NAME': 'Custom Component',
            'VERSION': self.get(self.device_oid + '.4.0'),
            'MANUFACTURER': 'My Vendor'
        }
        device.add_firmware(firmware)
    """)
    
    print("\n" + "=" * 70)
    print("See ExampleMibSupport class above for a complete working example.")
