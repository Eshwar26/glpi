#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Hardware - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname


class Hardware(InventoryModule):
    """AIX Hardware inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        uname_l = uname("-L")
        # LPAR partition can access the serial number of the host computer
        if uname_l and re.match(r'^(\d+)\s+(\S+)', uname_l):
            if inventory:
                inventory.set_hardware({
                    'VMSYSTEM': 'AIX_LPAR',
                })
