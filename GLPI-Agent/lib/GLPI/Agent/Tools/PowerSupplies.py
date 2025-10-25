#!/usr/bin/env python3
"""
GLPI Agent PowerSupplies Tools - Python Implementation

This module provides functions to manage power supplies information.
"""

from typing import Dict, List, Optional, Any
import re


__all__ = [
    'powersupply_fields',
    'InventoryPowerSupplies',
    'PowerSupply'
]


# Cached fields list
_fields = []


def powersupply_fields() -> List[str]:
    """
    Get the list of supported/expected power supply fields.
    
    Returns:
        List of field names for power supplies
    """
    global _fields
    
    if not _fields:
        # Initialize with standard power supply fields
        # This would normally be loaded from Inventory object
        _fields = [
            'NAME', 'MANUFACTURER', 'SERIALNUMBER', 'MODEL', 'POWER_MAX',
            'STATUS', 'PLUGGED'
        ]
    
    return _fields


class InventoryPowerSupplies:
    """
    Manages a collection of power supplies for inventory.
    """
    
    def __init__(self, logger=None):
        """
        Initialize power supplies inventory.
        
        Args:
            logger: Logger object
        """
        self.logger = logger
        self.list = {}
    
    def add(self, powersupply_data: Dict[str, Any]):
        """
        Add a power supply to the list, replacing any existing one with same device ID.
        
        Args:
            powersupply_data: Dictionary containing power supply information
        """
        powersupply = PowerSupply(powersupply_data, logger=self.logger)
        device_id = powersupply.device_id()
        
        if device_id in self.list and self.logger:
            self.logger.debug(f"Replacing '{device_id}' powersupply")
        
        self.list[device_id] = powersupply
    
    def merge(self, powersupplies: List[Dict[str, Any]]):
        """
        Merge new power supplies with existing list.
        
        Args:
            powersupplies: List of power supply dictionaries to merge
        """
        # Handle the case where only one powersupply is found and deviceid may not
        # be complete in one case
        if len(self.list) == 1 and len(powersupplies) == 1:
            current_id = list(self.list.keys())[0]
            current = self.list[current_id]
            powersupply = PowerSupply(powersupplies[0], logger=self.logger)
            
            if (current_id != powersupply.device_id() and 
                current.serial() == powersupply.serial()):
                # Just rename key to permit the merge if serial matches
                self.list[powersupply.device_id()] = current
                del self.list[current_id]
        
        for data in powersupplies:
            powersupply = PowerSupply(data, logger=self.logger)
            device_id = powersupply.device_id()
            
            # Just add powersupply if it doesn't exist in list
            if device_id in self.list:
                self.list[device_id].merge(powersupply)
            else:
                self.list[device_id] = powersupply
    
    def get_list(self) -> List[Dict[str, Any]]:
        """
        Get sorted list of all power supplies.
        
        Returns:
            List of power supply dictionaries
        """
        sorted_powersupplies = sorted(self.list.values(), key=lambda ps: ps.device_id())
        return [ps.dump() for ps in sorted_powersupplies]


class PowerSupply:
    """
    Represents a single power supply with its properties.
    """
    
    def __init__(self, powersupply_data: Dict[str, Any], logger=None):
        """
        Initialize power supply from data dictionary.
        
        Args:
            powersupply_data: Dictionary containing power supply information
            logger: Logger object
        """
        if isinstance(powersupply_data, PowerSupply):
            # Already a PowerSupply object
            self.data = powersupply_data.data.copy()
            self.logger = powersupply_data.logger
        else:
            self.data = powersupply_data.copy() if powersupply_data else {}
            self.logger = logger
    
    def device_id(self) -> str:
        """
        Get device ID.
        
        Returns:
            Unique device identifier
        """
        return self.vendor() + self.serial()
    
    def serial(self) -> str:
        """Get power supply serial number."""
        return self.data.get('SERIALNUMBER', '0')
    
    def vendor(self) -> str:
        """Get power supply vendor/manufacturer."""
        return self.data.get('MANUFACTURER', '')
    
    def merge(self, powersupply: 'PowerSupply'):
        """
        Merge another power supply's data into this one.
        
        Args:
            powersupply: PowerSupply object to merge from
        """
        for key in powersupply_fields():
            if key not in powersupply.data:
                continue
            
            # Don't replace value if they are the same, case insensitive check
            if (key in self.data and 
                re.match(f"^{re.escape(str(self.data[key]))}$", 
                        str(powersupply.data[key]), re.IGNORECASE)):
                continue
            
            if key in self.data and self.logger:
                self.logger.debug(
                    f"Replacing {key} value '{self.data[key]}' by "
                    f"'{powersupply.data[key]}' on '{self.device_id()}' powersupply"
                )
            
            self.data[key] = powersupply.data[key]
    
    def dump(self) -> Dict[str, Any]:
        """
        Dump power supply data dictionary with only valid fields.
        
        Returns:
            Dictionary containing power supply information
        """
        dump = {}
        
        for key in powersupply_fields():
            if key in self.data:
                dump[key] = self.data[key]
        
        return dump


if __name__ == '__main__':
    print("GLPI Agent PowerSupplies Tools")
    print("Available classes and functions:")
    for item in __all__:
        print(f"  - {item}")
    
    # Test functions
    print("\nTesting powersupply_fields:")
    print(f"  Fields: {powersupply_fields()}")
    
    print("\nTesting PowerSupply class:")
    ps = PowerSupply({
        'NAME': 'PSU1',
        'MANUFACTURER': 'Delta',
        'SERIALNUMBER': 'ABC123',
        'POWER_MAX': '750W'
    })
    print(f"  Device ID: {ps.device_id()}")
    print(f"  Serial: {ps.serial()}")
    print(f"  Vendor: {ps.vendor()}")
