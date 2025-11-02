#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Bios - Python Implementation
"""

from typing import Any, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import has_folder, can_read, get_first_line
from GLPI.Agent.Tools.Generic import is_invalid_bios_value


class Bios(InventoryModule):
    """Linux BIOS detection module via /sys/class/dmi/id."""
    
    category = "bios"
    
    # Only run this module if dmidecode has not been found
    runMeIfTheseChecksFailed = [
        "GLPI::Agent::Task::Inventory::Generic::Dmidecode::Bios"
    ]
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return has_folder('/sys/class/dmi/id')
    
    @staticmethod
    def _dmi_info(info: str) -> Optional[str]:
        """Read DMI information from sysfs."""
        class_path = f'/sys/class/dmi/id/{info}'
        if has_folder(class_path):
            return None
        if not can_read(class_path):
            return None
        return get_first_line(file=class_path)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        bios = {}
        
        bios_map = {
            'BMANUFACTURER': 'bios_vendor',
            'BDATE': 'bios_date',
            'BVERSION': 'bios_version',
            'ASSETTAG': 'chassis_asset_tag',
            'SMODEL': 'product_name',
            'SMANUFACTURER': 'sys_vendor',
            'SSN': 'product_serial',
            'MMODEL': 'board_name',
            'MMANUFACTURER': 'board_vendor',
            'MSN': 'board_serial',
        }
        
        for key, dmi_key in bios_map.items():
            value = Bios._dmi_info(dmi_key)
            if value is None:
                continue
            if is_invalid_bios_value(value):
                continue
            bios[key] = value
        
        # Fix issue #311: 'product_version' is a better 'SMODEL' for Lenovo systems
        system_version = Bios._dmi_info('product_version')
        if (system_version and bios.get('SMANUFACTURER') and
            bios['SMANUFACTURER'].upper() == 'LENOVO'):
            import re
            if re.match(r'^(Think|Idea|Yoga|Netfinity|Netvista|Intelli)', system_version, re.IGNORECASE):
                bios['SMODEL'] = system_version
        
        # Set Virtualbox VM S/N to UUID if found serial is '0'
        uuid = Bios._dmi_info('product_uuid')
        if (uuid and bios.get('MMODEL') == 'VirtualBox' and
            bios.get('SSN') == '0' and bios.get('MSN') == '0'):
            bios['SSN'] = uuid
        
        if inventory:
            inventory.set_bios(bios)
