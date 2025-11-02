#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Batteries Upower - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_canonical_manufacturer
from GLPI.Agent.Tools.Batteries import (
    Batteries,
    sanitize_battery_serial,
    get_canonical_voltage,
    get_canonical_capacity
)


class Upower(InventoryModule):
    """Linux UPower battery inventory module."""
    
    # Define some kind of priority so we can update batteries inventory
    runAfterIfEnabled = [
        'GLPI::Agent::Task::Inventory::Generic::Dmidecode::Battery',
    ]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('upower')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        logger = params.get('logger')
        inventory = params.get('inventory')
        
        batteries = Batteries(logger=logger)
        section = inventory.get_section('BATTERIES') if inventory else []
        
        # Empty current BATTERIES section into a new batteries list
        if section:
            for battery in section:
                batteries.add(battery)
        
        # Merge batteries reported by upower
        new_batteries = Upower._get_batteries_from_upower(logger=logger)
        batteries.merge(new_batteries)
        
        # Add back merged batteries into inventories
        for battery in batteries.list():
            if inventory:
                inventory.add_entry(
                    section='BATTERIES',
                    entry=battery
                )
    
    @staticmethod
    def _get_batteries_from_upower(**params) -> List[Dict[str, Any]]:
        """Get batteries from upower command."""
        battery_names = Upower._get_batteries_name_from_upower(**params)
        
        if not battery_names:
            return []
        
        batteries = []
        for batt_name in battery_names:
            battery = Upower._get_battery_from_upower(
                name=batt_name,
                **params
            )
            if battery:
                batteries.append(battery)
        
        return batteries
    
    @staticmethod
    def _get_batteries_name_from_upower(**params) -> List[str]:
        """Get battery names from upower enumerate."""
        lines = get_all_lines(
            command='upower --enumerate',
            **params
        )
        
        if not lines:
            return []
        
        batt_names = []
        for line in lines:
            match = re.match(r'^(.*\/battery_\S+)$', line)
            if match:
                batt_names.append(match.group(1))
        
        return batt_names
    
    @staticmethod
    def _get_battery_from_upower(**params) -> Optional[Dict[str, Any]]:
        """Get single battery from upower."""
        name = params.get('name')
        if name:
            params['command'] = f'upower -i {name}'
        
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        data = {}
        for line in lines:
            match = re.match(r'^\s*(\S+):\s*(\S+(?:\s+\S+)*)$', line)
            if match:
                data[match.group(1)] = match.group(2)
        
        battery = {
            'NAME': data.get('model', ''),
            'CHEMISTRY': data.get('technology', ''),
            'SERIAL': sanitize_battery_serial(data.get('serial', '')),
        }
        
        manufacturer = data.get('vendor') or data.get('manufacturer')
        if manufacturer:
            battery['MANUFACTURER'] = get_canonical_manufacturer(manufacturer)
        
        voltage = get_canonical_voltage(data.get('voltage'))
        if voltage:
            battery['VOLTAGE'] = voltage
        
        capacity = get_canonical_capacity(data.get('energy-full-design'), voltage)
        if capacity:
            battery['CAPACITY'] = capacity
        
        real_capacity = get_canonical_capacity(data.get('energy-full'), voltage)
        if real_capacity is not None and str(real_capacity):
            battery['REAL_CAPACITY'] = real_capacity
        
        return battery
