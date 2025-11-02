#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Batteries SysClass - Python Implementation
"""

from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import glob_files, get_first_line, has_file, get_canonical_manufacturer
from GLPI.Agent.Tools.Batteries import (
    Batteries,
    sanitize_battery_serial,
    get_canonical_capacity
)


class SysClass(InventoryModule):
    """Linux sysfs battery inventory module."""
    
    # Define some kind of priority so we can update batteries inventory
    runAfterIfEnabled = [
        'GLPI::Agent::Task::Inventory::Generic::Dmidecode::Battery',
        'GLPI::Agent::Task::Inventory::Generic::Batteries::Acpiconf',
        'GLPI::Agent::Task::Inventory::Generic::Batteries::Upower',
    ]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return bool(glob_files("/sys/class/power_supply/*/capacity"))
    
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
        
        # Merge batteries reported by sysfs
        new_batteries = SysClass._get_batteries_from_sysclass(logger=logger)
        batteries.merge(new_batteries)
        
        # Add back merged batteries into inventories
        for battery in batteries.list():
            if inventory:
                inventory.add_entry(
                    section='BATTERIES',
                    entry=battery
                )
    
    @staticmethod
    def _get_batteries_from_sysclass(**params) -> List[Dict[str, Any]]:
        """Get batteries from sysfs."""
        batteries = []
        
        for psu in glob_files("/sys/class/power_supply/*"):
            psu_type = get_first_line(file=f"{psu}/type")
            if not psu_type:
                continue
            
            if not get_first_line(file=f"{psu}/present"):
                continue
            
            if psu_type != "Battery" or not has_file(f"{psu}/capacity"):
                continue
            
            battery = SysClass._get_battery_from_sysclass(
                psu=psu,
                **params
            )
            if battery:
                batteries.append(battery)
        
        return batteries
    
    @staticmethod
    def _get_battery_from_sysclass(**params) -> Optional[Dict[str, Any]]:
        """Get single battery from sysfs."""
        psu = params.get('psu')
        if not psu:
            return None
        
        battery = {
            'NAME': get_first_line(file=f"{psu}/model_name") or '',
            'CHEMISTRY': get_first_line(file=f"{psu}/technology") or '',
            'SERIAL': sanitize_battery_serial(
                get_first_line(file=f"{psu}/serial_number") or ''
            ),
        }
        
        manufacturer = get_first_line(file=f"{psu}/manufacturer")
        if manufacturer:
            battery['MANUFACTURER'] = get_canonical_manufacturer(manufacturer)
        
        # Voltage is provided in µV
        voltage_str = get_first_line(file=f"{psu}/voltage_min_design")
        if voltage_str:
            try:
                voltage = int(voltage_str)
                battery['VOLTAGE'] = int(voltage / 1000)
            except ValueError:
                pass
        
        # Energy full design is provided in µWh
        capacity_str = get_first_line(file=f"{psu}/energy_full_design")
        if capacity_str:
            try:
                capacity = int(capacity_str)
                battery['CAPACITY'] = int(capacity / 1000)
            except ValueError:
                pass
        
        # Charge full design is provided in µAh
        if not capacity_str:
            charge_str = get_first_line(file=f"{psu}/charge_full_design")
            if charge_str and battery.get('VOLTAGE'):
                try:
                    charge = int(charge_str)
                    capacity = get_canonical_capacity(
                        f"{int(charge/1000)} mAh",
                        battery['VOLTAGE']
                    )
                    if capacity:
                        battery['CAPACITY'] = capacity
                except ValueError:
                    pass
        
        # Real energy is provided in µWh
        real_capacity_str = get_first_line(file=f"{psu}/energy_full")
        if real_capacity_str:
            try:
                real_capacity = int(real_capacity_str)
                battery['REAL_CAPACITY'] = int(real_capacity / 1000)
            except ValueError:
                pass
        
        # Real charge is provided in µAh
        if not real_capacity_str:
            real_charge_str = get_first_line(file=f"{psu}/charge_full")
            if real_charge_str and battery.get('VOLTAGE'):
                try:
                    real_charge = int(real_charge_str)
                    real_cap = get_canonical_capacity(
                        f"{int(real_charge/1000)} mAh",
                        battery['VOLTAGE']
                    )
                    if real_cap:
                        battery['REAL_CAPACITY'] = real_cap
                except ValueError:
                    pass
        
        return battery
