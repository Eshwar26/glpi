#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Controllers - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Controllers(InventoryModule):
    """Solaris controllers detection module."""
    
    category = "controller"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('cfgadm')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        lines = get_all_lines(
            command='cfgadm -s cols=ap_id:type:info',
            logger=logger
        )
        if not lines:
            return
        
        for line in lines:
            if line.startswith('Ap_Id'):
                continue
            match = re.match(r'^(\S+)\s+(\S+)\s+(\S+)', line)
            if not match:
                continue
            
            name = match.group(1)
            controller_type = match.group(2)
            manufacturer = match.group(3)
            
            if inventory:
                inventory.add_entry(
                    section='CONTROLLERS',
                    entry={
                        'NAME': name,
                        'MANUFACTURER': manufacturer,
                        'TYPE': controller_type,
                    }
                )
