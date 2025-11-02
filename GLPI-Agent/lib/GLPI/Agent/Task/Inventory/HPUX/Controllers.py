#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Controllers - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Controllers(InventoryModule):
    """HP-UX controllers detection module."""
    
    category = "controller"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ioscan')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for controller_type in ['ext_bus', 'fc', 'psi']:
            for controller in Controllers._get_controllers(
                command=f"ioscan -kFC {controller_type}",
                logger=logger
            ):
                if inventory:
                    inventory.add_entry(
                        section='CONTROLLERS',
                        entry=controller
                    )
    
    @staticmethod
    def _get_controllers(**params) -> List[Dict[str, str]]:
        """Parse ioscan output for controllers."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        controllers = []
        for line in lines:
            info = line.split(':')
            if len(info) > 17:
                controllers.append({
                    'TYPE': info[17]
                })
        
        return controllers
