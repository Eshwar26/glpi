#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Battery - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_dmidecode_infos
from GLPI.Agent.Tools import get_canonical_manufacturer
from GLPI.Agent.Tools.Batteries import sanitize_battery_serial, get_canonical_voltage, get_canonical_capacity


class Battery(InventoryModule):
    """Dmidecode battery inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "battery"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        batteries = Battery._get_batteries(logger=logger)
        
        for battery in batteries:
            if inventory:
                inventory.add_entry(
                    section='BATTERIES',
                    entry=battery
                )
    
    @staticmethod
    def _get_batteries(**params) -> List[Dict[str, Any]]:
        """Get batteries from dmidecode."""
        infos = get_dmidecode_infos(**params)
        
        if not infos or not infos.get(22):
            return []
        
        batteries = []
        for info in infos[22]:
            battery = Battery._extract_battery_data(info)
            if battery:
                batteries.append(battery)
        
        return batteries
    
    @staticmethod
    def _extract_battery_data(info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract battery data from dmidecode info."""
        # Skip battery data without enough infos
        if not (info.get('Name') and info.get('Manufacturer')):
            return None
        
        if not (info.get('Serial Number') or info.get('SBDS Serial Number')):
            return None
        
        if not (info.get('Chemistry') or info.get('SBDS Chemistry')):
            return None
        
        battery = {
            'NAME': info.get('Name'),
            'MANUFACTURER': get_canonical_manufacturer(info.get('Manufacturer')),
            'SERIAL': sanitize_battery_serial(
                info.get('Serial Number') or info.get('SBDS Serial Number')
            ),
            'CHEMISTRY': info.get('Chemistry') or info.get('SBDS Chemistry'),
        }
        
        # Parse manufacture date
        if info.get('Manufacture Date'):
            date = Battery._parse_date(info['Manufacture Date'])
            if date:
                battery['DATE'] = date
        elif info.get('SBDS Manufacture Date'):
            date = Battery._parse_date(info['SBDS Manufacture Date'])
            if date:
                battery['DATE'] = date
        
        # Parse voltage
        voltage = get_canonical_voltage(info.get('Design Voltage'))
        if voltage:
            battery['VOLTAGE'] = voltage
        
        # Parse capacity
        capacity = get_canonical_capacity(info.get('Design Capacity'), voltage)
        if capacity:
            battery['CAPACITY'] = capacity
        
        return battery
    
    @staticmethod
    def _parse_date(string: str) -> Optional[str]:
        """Parse date from various formats."""
        # Format: MM/DD/YYYY or MM-DD-YYYY
        match = re.match(r'(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})', string)
        if match:
            month, day, year = match.groups()
            return f"{day}/{month}/{year}"
        
        # Format: YYYY/MM/DD or YYYY-MM-DD
        match = re.match(r'(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})', string)
        if match:
            year, month, day = match.groups()
            return f"{day}/{month}/{year}"
        
        # Format: MM/DD/YY or MM-DD-YY
        match = re.match(r'(\d{1,2})[\/-](\d{1,2})[\/-](\d{2})', string)
        if match:
            month, day, year_short = match.groups()
            year_int = int(year_short)
            year = ("19" if year_int > 90 else "20") + year_short
            return f"{day}/{month}/{year}"
        
        return None
