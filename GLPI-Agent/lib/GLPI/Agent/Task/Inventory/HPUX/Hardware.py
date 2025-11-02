#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Hardware - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.HPUX import get_info_from_machinfo


class Hardware(InventoryModule):
    """HP-UX hardware detection module."""
    
    category = "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        hardware = {}
        
        if can_run('/usr/contrib/bin/machinfo'):
            info = get_info_from_machinfo(logger=logger)
            if info:
                platform_info = info.get('Platform info', {})
                machine_id = platform_info.get('machine id number')
                if machine_id:
                    hardware['UUID'] = machine_id.upper()
        
        if hardware and inventory:
            inventory.set_hardware(hardware)
