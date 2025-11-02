#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Batteries Acpiconf - Python Implementation
"""

from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Batteries import (
    Batteries,
    sanitize_battery_serial,
    get_canonical_voltage,
    get_canonical_capacity
)


class Acpiconf(InventoryModule):
    """BSD Acpiconf battery inventory module."""
    
    # Define some kind of priority so we can update batteries inventory
    runAfterIfEnabled = [
        'GLPI::Agent::Task::Inventory::Generic::Dmidecode::Battery',
        'GLPI::Agent::Task::Inventory::Generic::Batteries::Upower',
    ]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('acpiconf')
    
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
        
        # Merge batteries reported by acpiconf
        new_batteries = Acpiconf._get_batteries_from_acpiconf(logger=logger)
        batteries.merge(new_batteries)
        
        # Add back merged batteries into inventories
        for battery in batteries.list():
            if inventory:
                inventory.add_entry(
                    section='BATTERIES',
                    entry=battery
                )
    
    @staticmethod
    def _get_batteries_from_acpiconf(**params) -> List[Dict[str, Any]]:
        """Get batteries from acpiconf command."""
        batteries = []
        index = 0
        
        while True:
            battery = Acpiconf._get_battery_from_acpiconf(
                index=index,
                **params
            )
            if not battery:
                break
            batteries.append(battery)
            index += 1
        
        return batteries
    
    @staticmethod
    def _get_battery_from_acpiconf(**params) -> Optional[Dict[str, Any]]:
        """Get single battery from acpiconf."""
        index = params.get('index')
        if index is not None:
            params['command'] = f'acpiconf -i {index}'
        
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        data = {}
        for line in lines:
            match = line.split(':', 1)
            if len(match) == 2:
                key = match[0].strip()
                value = match[1].strip()
                data[key] = value
        
        battery = {
            'NAME': data.get('Model number', ''),
            'CHEMISTRY': data.get('Type', ''),
            'SERIAL': sanitize_battery_serial(data.get('Serial number', '')),
        }
        
        voltage = get_canonical_voltage(data.get('Design voltage'))
        if voltage:
            battery['VOLTAGE'] = voltage
        
        capacity = get_canonical_capacity(data.get('Design capacity'), voltage)
        if capacity:
            battery['CAPACITY'] = capacity
        
        real_capacity = get_canonical_capacity(data.get('Last full capacity'), voltage)
        if real_capacity:
            battery['REAL_CAPACITY'] = real_capacity
        
        return battery
