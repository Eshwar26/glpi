#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD CPU - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line
from GLPI.Agent.Tools.Generic import get_cpus_from_dmidecode


class CPU(InventoryModule):
    """BSD CPU inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('dmidecode')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        speed = None
        hw_model = get_first_line(command='sysctl -n hw.model')
        if hw_model:
            match = re.search(r'([\.\d]+)GHz', hw_model)
            if match:
                speed = float(match.group(1)) * 1000
        
        cpus = get_cpus_from_dmidecode()
        for cpu in cpus:
            if speed:
                cpu['SPEED'] = speed
            
            if inventory:
                inventory.add_entry(
                    section='CPUS',
                    entry=cpu
                )
