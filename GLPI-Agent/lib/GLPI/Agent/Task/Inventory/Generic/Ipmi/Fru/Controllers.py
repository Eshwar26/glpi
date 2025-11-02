#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Ipmi Fru Controllers - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.IpmiFru import get_ipmi_fru, parse_fru


class Controllers(InventoryModule):
    """IPMI FRU controllers inventory module."""
    
    CONTROLLERS = re.compile(
        r'^(?:BP|PERC|NDC|Ethernet\s+Adptr|SAS\s+Ctlr)\d*\s+',
        re.VERBOSE
    )
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "controller"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        fru = get_ipmi_fru(**params)
        if not fru:
            return
        
        fru_keys = [key for key in fru.keys() if Controllers.CONTROLLERS.match(key)]
        if not fru_keys:
            return
        
        fields = inventory.get_fields().get('CONTROLLERS')
        for descr in fru_keys:
            ctrl = parse_fru(fru[descr], fields)
            if not ctrl:
                continue
            
            # Extract type from description
            match = re.match(r'^([\w\s]+[a-zA-Z])', descr)
            if match:
                ctrl['TYPE'] = match.group(1)
            
            if inventory:
                inventory.add_entry(
                    section='CONTROLLERS',
                    entry=ctrl
                )
