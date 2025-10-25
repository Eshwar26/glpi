#!/usr/bin/env python3
"""
GLPI Agent USB Tools - Python Implementation

This is an abstract base class for USB device objects.
"""

import os
import glob
import importlib
from typing import Optional, Dict, Any

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import empty
    from GLPI.Agent.Tools.Generic import get_usb_device_vendor
except ImportError:
    # Mock for standalone usage
    def empty(val):
        return not val
    
    def get_usb_device_vendor(**params):
        return None


__all__ = [
    'USBDevice'
]


class USBDevice:
    """
    Base class for USB device objects with dynamic subclass loading.
    """
    
    _loaded_modules = {}
    
    def __init__(self, vendorid: Optional[str] = None, productid: Optional[str] = None,
                 caption: Optional[str] = None, name: Optional[str] = None,
                 serial: Optional[str] = None, logger=None, reload: bool = False):
        """
        Initialize USB device.
        
        Args:
            vendorid: USB vendor ID
            productid: USB product ID
            caption: Device caption
            name: Device name
            serial: Device serial number
            logger: Logger object
            reload: Force reload of submodules (for testing)
        """
        self.logger = logger
        self._vendorid = vendorid or ""
        self._productid = productid or ""
        self._caption = caption or ""
        self._name = name or ""
        self._serial = serial or ""
        self._manufacturer = ""
        
        # Load and try subclass modules
        self._load_subclasses(reload=reload)
    
    def _load_subclasses(self, reload: bool = False):
        """Load USB device subclass modules and check for support."""
        # Get the directory containing this module
        module_dir = os.path.dirname(os.path.abspath(__file__))
        usb_dir = os.path.join(module_dir, 'USB')
        
        if not os.path.isdir(usb_dir):
            return
        
        # Find all Python files in the USB directory
        pattern = os.path.join(usb_dir, '*.py')
        
        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)
            
            # Skip __init__.py
            if filename.startswith('__'):
                continue
            
            # Get module name without .py extension
            module_name = filename[:-3]
            full_module_name = f'GLPI.Agent.Tools.USB.{module_name}'
            
            # Check if module should be loaded
            if full_module_name in USBDevice._loaded_modules and not reload:
                if not USBDevice._loaded_modules[full_module_name]:
                    continue
            else:
                try:
                    module = importlib.import_module(full_module_name)
                    
                    # Check if module is enabled
                    if hasattr(module, 'enabled'):
                        enabled = module.enabled()
                    else:
                        enabled = True
                    
                    USBDevice._loaded_modules[full_module_name] = enabled
                    
                    if not enabled:
                        continue
                    
                    # Find the USB device class in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        
                        # Check if it's a class that inherits from USBDevice
                        if (isinstance(attr, type) and 
                            issubclass(attr, USBDevice) and 
                            attr != USBDevice):
                            
                            # Change instance class
                            self.__class__ = attr
                            
                            # Check if this subclass supports this device
                            if self.supported():
                                return
                            
                except Exception as e:
                    if self.logger:
                        self.logger.info(f"{full_module_name} require error: {e}")
                    USBDevice._loaded_modules[full_module_name] = False
                    continue
        
        # Reset to base USB device without specific support
        self.__class__ = USBDevice
    
    @staticmethod
    def enabled() -> bool:
        """
        Check if module should be enabled (to be overridden in subclasses).
        
        Returns:
            True if module should be enabled
        """
        return True
    
    def supported(self) -> bool:
        """
        Check if this subclass supports the device (to be overridden in subclasses).
        
        Returns:
            True if device is supported by this subclass
        """
        return False
    
    def update(self):
        """Update device information (to be overridden in subclasses)."""
        pass
    
    def update_by_ids(self):
        """Update device by checking usb.ids database."""
        if not empty(self._vendorid):
            vendor = get_usb_device_vendor(
                logger=self.logger,
                id=self._vendorid.lower()
            )
            
            if vendor:
                if not empty(vendor.get('name')):
                    self._manufacturer = vendor['name']
                
                if not empty(self._productid):
                    devices = vendor.get('devices', {})
                    entry = devices.get(self._productid.lower())
                    
                    if entry and not empty(entry.get('name')):
                        self._caption = entry['name']
                        self._name = entry['name']
    
    def vendorid(self) -> str:
        """Get vendor ID."""
        return self._vendorid
    
    def productid(self) -> str:
        """Get product ID."""
        return self._productid
    
    def serial(self, serial: Optional[str] = None) -> str:
        """
        Get or set serial number.
        
        Args:
            serial: Serial number to set (optional)
            
        Returns:
            Serial number
        """
        if serial is not None:
            self._serial = serial
        return self._serial
    
    def delete_serial(self):
        """Delete serial number."""
        self._serial = ""
    
    def skip(self) -> bool:
        """
        Check if device should be skipped.
        
        Returns:
            True if device should be skipped
        """
        # Skip for invalid vendorid
        if empty(self._vendorid):
            return True
        
        # Skip if vendorid is all zeros
        if self._vendorid.replace('0', '') == '':
            return True
        
        return False
    
    def dump(self) -> Dict[str, str]:
        """
        Dump device data for inventory.
        
        Returns:
            Dictionary containing device information
        """
        dump = {}
        
        # Mapping of internal attributes to output keys
        keymap = {
            '_caption': 'CAPTION',
            '_name': 'NAME',
            '_vendorid': 'VENDORID',
            '_productid': 'PRODUCTID',
            '_serial': 'SERIAL',
            '_manufacturer': 'MANUFACTURER'
        }
        
        for attr, key in keymap.items():
            value = getattr(self, attr, None)
            if not empty(value):
                dump[key] = value
        
        return dump


if __name__ == '__main__':
    print("GLPI Agent USB Tools")
    print("Available classes:")
    for cls in __all__:
        print(f"  - {cls}")
    
    # Test with sample USB device
    print("\nTesting USBDevice class:")
    device = USBDevice(
        vendorid='046d',
        productid='c52b',
        caption='USB Receiver',
        serial='12345'
    )
    
    print(f"  Vendor ID: {device.vendorid()}")
    print(f"  Product ID: {device.productid()}")
    print(f"  Serial: {device.serial()}")
    print(f"  Skip: {device.skip()}")
    print(f"  Dump: {device.dump()}")
