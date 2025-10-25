#!/usr/bin/env python3
"""
GLPI Agent Batteries Tools - Python Implementation

This module provides functions to manage batteries information.
"""

from typing import Dict, List, Optional, Any
import re

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import trim_whitespace, hex2dec
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import trim_whitespace, hex2dec


__all__ = [
    'battery_fields',
    'sanitize_battery_serial',
    'get_canonical_voltage',
    'get_canonical_capacity'
]


# Cached fields list
_fields = []


def battery_fields() -> List[str]:
    """
    Get the list of supported/expected battery fields.
    
    Returns:
        List of field names for batteries
    """
    global _fields
    
    if not _fields:
        # Initialize with standard battery fields
        # This would normally be loaded from Inventory object
        _fields = [
            'NAME', 'MANUFACTURER', 'SERIAL', 'MODEL', 'TYPE',
            'CAPACITY', 'VOLTAGE', 'CHEMISTRY', 'DATE', 
            'REAL_CAPACITY', 'SERIAL_NUMBER'
        ]
    
    return _fields


def sanitize_battery_serial(serial: Optional[str]) -> str:
    """
    Clean and normalize battery serial number.
    
    Args:
        serial: Raw battery serial number
        
    Returns:
        Cleaned serial number, returns '0' if not defined or invalid
    """
    # Simply return a '0' serial if not defined
    if not serial:
        return '0'
    
    # Simplify zeros-only serial
    if re.match(r'^0+$', serial):
        return '0'
    
    # Return trimmed whitespace if not hexadecimal
    if not re.match(r'^[0-9A-F]+$', serial, re.IGNORECASE):
        return trim_whitespace(serial)
    
    # Prepare to keep serial as decimal if we have recognized it as hexadecimal
    if re.search(r'[a-f]', serial, re.IGNORECASE) or serial.startswith('0'):
        serial = '0x' + serial
    
    # Convert as decimal string
    return str(hex2dec(serial))


def get_canonical_voltage(value: Optional[str]) -> Optional[int]:
    """
    Get canonical voltage in millivolts (mV).
    
    Args:
        value: Voltage string with unit (e.g., "12.5V" or "12500mV")
        
    Returns:
        Voltage in mV or None if invalid
    """
    if not value:
        return None
    
    match = re.match(r'^([,.\d]+)\s*(m?V)$', value, re.IGNORECASE | re.VERBOSE)
    if not match:
        return None
    
    voltage = match.group(1).replace(',', '.')
    unit = match.group(2).lower()
    
    voltage_float = float(voltage)
    
    # Convert to millivolts
    return int(voltage_float) if unit == 'mv' else int(voltage_float * 1000)


def get_canonical_capacity(value: Optional[str], voltage: Optional[int] = None) -> Optional[int]:
    """
    Get canonical capacity in milliwatt-hours (mWh).
    
    Args:
        value: Capacity string with unit (e.g., "50Wh", "5000mAh")
        voltage: Voltage in mV (required for Ah/mAh conversions)
        
    Returns:
        Capacity in mWh or None if invalid
    """
    if not value:
        return None
    
    match = re.match(r'^([,.\d]+)\s*(m?[WA]?h)$', value, re.IGNORECASE | re.VERBOSE)
    if not match:
        return None
    
    capacity = float(match.group(1).replace(',', '.'))
    unit = match.group(2)
    
    # We expect to return capacity in mWh, voltage is expected to be in mV
    if re.match(r'^mWh$', unit, re.IGNORECASE):
        return int(capacity)
    elif re.match(r'^Wh$', unit, re.IGNORECASE):
        return int(capacity * 1000)
    elif re.match(r'^mAh$', unit, re.IGNORECASE):
        if not voltage:
            return None
        return int(capacity * voltage / 1000)
    elif re.match(r'^Ah$', unit, re.IGNORECASE):
        if not voltage:
            return None
        return int(capacity * voltage)
    
    return None


class InventoryBatteries:
    """
    Manages a collection of batteries for inventory.
    """
    
    def __init__(self, logger=None):
        """
        Initialize batteries inventory.
        
        Args:
            logger: Logger object
        """
        self.logger = logger
        self.list = {}
    
    def add(self, battery_data: Dict[str, Any]):
        """
        Add a battery to the list, replacing any existing battery with same device ID.
        
        Args:
            battery_data: Dictionary containing battery information
        """
        battery = Battery(battery_data, logger=self.logger)
        device_id = battery.device_id()
        
        if device_id in self.list and self.logger:
            self.logger.debug(f"Replacing '{device_id}' battery")
        
        self.list[device_id] = battery
    
    def merge(self, batteries: List[Dict[str, Any]]):
        """
        Merge new batteries with existing list.
        
        Args:
            batteries: List of battery dictionaries to merge
        """
        # Handle the case where only one battery is found and deviceid may not
        # be complete in one case
        if len(self.list) == 1 and len(batteries) == 1:
            current_id = list(self.list.keys())[0]
            current = self.list[current_id]
            battery = Battery(batteries[0], logger=self.logger)
            
            if (current_id != battery.device_id() and 
                current.serial() == battery.serial() and 
                current.model() == battery.model()):
                # Just rename key to permit the merge if serial and model match
                self.list[battery.device_id()] = current
                del self.list[current_id]
        
        for data in batteries:
            battery = Battery(data, logger=self.logger)
            device_id = battery.device_id()
            
            # Just add battery if it doesn't exist in list
            if device_id in self.list:
                self.list[device_id].merge(battery)
            else:
                self.list[device_id] = battery
    
    def get_list(self) -> List[Dict[str, Any]]:
        """
        Get sorted list of all batteries.
        
        Returns:
            List of battery dictionaries
        """
        sorted_batteries = sorted(self.list.values(), key=lambda b: b.device_id())
        return [battery.dump() for battery in sorted_batteries]


class Battery:
    """
    Represents a single battery with its properties.
    """
    
    def __init__(self, battery_data: Dict[str, Any], logger=None):
        """
        Initialize battery from data dictionary.
        
        Args:
            battery_data: Dictionary containing battery information
            logger: Logger object
        """
        if isinstance(battery_data, Battery):
            # Already a Battery object
            self.data = battery_data.data.copy()
            self.logger = battery_data.logger
        else:
            self.data = battery_data.copy() if battery_data else {}
            self.logger = logger
    
    def device_id(self) -> str:
        """
        Get device ID inspired by the WMI used one on Win32 systems.
        
        Returns:
            Unique device identifier
        """
        return self.serial() + self.manufacturer() + self.model()
    
    def serial(self) -> str:
        """Get battery serial number."""
        return self.data.get('SERIAL', '0')
    
    def manufacturer(self) -> str:
        """Get battery manufacturer."""
        return self.data.get('MANUFACTURER', '')
    
    def model(self) -> str:
        """Get battery model."""
        return self.data.get('MODEL', '')
    
    def merge(self, battery: 'Battery'):
        """
        Merge another battery's data into this one.
        
        Args:
            battery: Battery object to merge from
        """
        for key in battery_fields():
            if key not in battery.data:
                continue
            
            # Don't replace value if they are the same, case insensitive check
            if (key in self.data and 
                re.match(f"^{re.escape(str(self.data[key]))}$", 
                        str(battery.data[key]), re.IGNORECASE)):
                continue
            
            if key in self.data and self.logger:
                self.logger.debug(
                    f"Replacing {key} value '{self.data[key]}' by "
                    f"'{battery.data[key]}' on '{self.device_id()}' battery"
                )
            
            self.data[key] = battery.data[key]
    
    def dump(self) -> Dict[str, Any]:
        """
        Dump battery data dictionary with only valid fields.
        
        Returns:
            Dictionary containing battery information
        """
        dump = {}
        
        for key in battery_fields():
            if key in self.data:
                dump[key] = self.data[key]
        
        return dump


if __name__ == '__main__':
    # Basic testing
    print("GLPI Agent Batteries Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
    
    # Test functions
    print("\nTesting sanitize_battery_serial:")
    print(f"  sanitize_battery_serial('00000'): {sanitize_battery_serial('00000')}")
    print(f"  sanitize_battery_serial('ABC123'): {sanitize_battery_serial('ABC123')}")
    
    print("\nTesting get_canonical_voltage:")
    print(f"  get_canonical_voltage('12.5V'): {get_canonical_voltage('12.5V')}")
    print(f"  get_canonical_voltage('12500mV'): {get_canonical_voltage('12500mV')}")
    
    print("\nTesting get_canonical_capacity:")
    print(f"  get_canonical_capacity('50Wh'): {get_canonical_capacity('50Wh')}")
    print(f"  get_canonical_capacity('5000mAh', 12000): {get_canonical_capacity('5000mAh', 12000)}")
