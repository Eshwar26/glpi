#!/usr/bin/env python3
"""
GLPI Agent USB Gertec Module - Python Implementation

USB device handler for Gertec devices.
Actually supported only on Windows.
"""

import platform
from typing import Optional

# Import the main USB device class
try:
    from GLPI.Agent.Tools.USB import USBDevice
    from GLPI.Agent.Tools import empty
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    # Mock for standalone usage
    class USBDevice:
        def __init__(self, **params):
            pass
        
        def vendorid(self):
            return ""
        
        def serial(self, serial=None):
            return ""
    
    def empty(val):
        return not val


__all__ = ['Gertec']


class Gertec(USBDevice):
    """
    Gertec USB device handler.
    """
    
    @staticmethod
    def enabled() -> bool:
        """
        Check if module should be enabled.
        Currently only supported on Windows.
        
        Returns:
            True if running on Windows
        """
        return platform.system() == 'Windows'
    
    def supported(self) -> bool:
        """
        Check if this device is a Gertec device.
        
        Returns:
            True if vendor ID matches Gertec (1753)
        """
        vendor_id = self.vendorid()
        return bool(vendor_id and vendor_id.upper() == '1753')
    
    def update(self):
        """
        Update device information.
        
        Currently implements serial number discovery from Windows registry.
        TODO: Implement full registry-based serial number discovery.
        """
        serial = None
        
        # TODO: Implement serial number discovery in registry
        # On Windows, Gertec device serial numbers can be found in the registry
        # under specific USB device keys
        
        if serial and not empty(serial):
            self.serial(serial)


if __name__ == '__main__':
    print("GLPI Agent USB Gertec Module")
    print(f"Enabled: {Gertec.enabled()}")
    print("USB device handler for Gertec devices")
