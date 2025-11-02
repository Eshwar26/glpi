#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Ipmi Fru Psu - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.IpmiFru import get_ipmi_fru, parse_fru
from GLPI.Agent.Inventory.PowerSupplies import PowerSupplies


class Psu(InventoryModule):
    """IPMI FRU PSU inventory module."""
    
    # Define a priority so we can update powersupplies inventory
    run_after_if_enabled = [
        'GLPI.Agent.Task.Inventory.Generic.Dmidecode.Psu'
    ]
    
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
        
        fru = get_ipmi_fru(**params)
        if not fru:
            return
        
        fru_keys = [key for key in fru.keys() if re.match(r'^(PS|Pwr Supply )\d+', key)]
        if not fru_keys:
            return
        
        # Empty current POWERSUPPLIES section into a new psu list
        psulist = PowerSupplies(logger=logger)
        section = inventory.get_section('POWERSUPPLIES') or []
        while section:
            powersupply = section.pop(0)
            psulist.add(powersupply)
        
        # Merge powersupplies reported by ipmitool
        fru_list = []
        fields = inventory.get_fields().get('POWERSUPPLIES')
        
        # Omit MODEL field as it's duplicate of PARTNUM field
        if 'MODEL' in fields:
            del fields['MODEL']
        
        for descr in sorted(fru_keys):
            fru_list.append(parse_fru(fru[descr], fields))
        
        psulist.merge(*fru_list)
        
        # Add back merged powersupplies into inventory
        for psu in psulist.list():
            if inventory:
                inventory.add_entry(
                    section='POWERSUPPLIES',
                    entry=psu
                )
