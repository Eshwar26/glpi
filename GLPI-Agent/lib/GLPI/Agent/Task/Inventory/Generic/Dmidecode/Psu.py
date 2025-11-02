#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Psu - Python Implementation
"""

import re
from typing import Any, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_canonical_manufacturer, get_canonical_power
from GLPI.Agent.Tools.Generic import get_dmidecode_infos
from GLPI.Agent.Tools.PartNumber import PartNumber


class Psu(InventoryModule):
    """Dmidecode PSU inventory module."""
    
    FIELDS = {
        'PARTNUM': 'Model Part Number',
        'SERIALNUMBER': 'Serial Number',
        'MANUFACTURER': 'Manufacturer',
        'NAME': 'Name',
        'STATUS': 'Status',
        'PLUGGED': 'Plugged',
        'LOCATION': 'Location',
        'POWER_MAX': 'Max Power Capacity',
        'HOTREPLACEABLE': 'Hot Replaceable',
    }
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "psu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        infos = get_dmidecode_infos(logger=logger)
        
        if not infos or not infos.get(39):
            return
        
        for info in infos[39]:
            # Skip battery
            if info.get('Type') and info['Type'] == 'Battery':
                continue
            
            psu = {}
            
            # Add available informations but filter out not filled values
            for key, field_name in Psu.FIELDS.items():
                if field_name not in info:
                    continue
                value = info[field_name]
                if re.search(r'To Be Filled By O\.?E\.?M', value, re.IGNORECASE):
                    continue
                if re.search(r'OEM Define', value, re.IGNORECASE):
                    continue
                psu[key] = value
            
            # Get canonical manufacturer
            if psu.get('MANUFACTURER'):
                psu['MANUFACTURER'] = get_canonical_manufacturer(psu['MANUFACTURER'])
            
            # Get canonical max power
            if psu.get('POWER_MAX'):
                psu['POWER_MAX'] = get_canonical_power(psu['POWER_MAX'])
            
            # Validate PartNumber, as example, this fixes Dell PartNumbers
            if psu.get('PARTNUM') and psu.get('MANUFACTURER'):
                partnumber_factory = PartNumber(logger=logger)
                partnumber = partnumber_factory.match(
                    partnumber=psu['PARTNUM'],
                    manufacturer=psu['MANUFACTURER'],
                    category='controller',
                )
                if partnumber:
                    psu['PARTNUM'] = partnumber.get()
            
            # Filter out PSU if nothing interesting is found
            if not psu:
                continue
            if not (psu.get('NAME') or psu.get('SERIALNUMBER') or psu.get('PARTNUM')):
                continue
            
            if inventory:
                inventory.add_entry(
                    section='POWERSUPPLIES',
                    entry=psu
                )
