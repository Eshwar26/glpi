#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Controllers - Python Implementation
"""

from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.AIX import get_adapters_from_lsdev


class Controllers(InventoryModule):
    """AIX Controllers inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "controller"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lsdev')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        controllers = Controllers._get_controllers(logger=logger)
        
        for controller in controllers:
            if inventory:
                inventory.add_entry(
                    section='CONTROLLERS',
                    entry=controller
                )
    
    @staticmethod
    def _get_controllers(**params) -> List[Dict[str, Any]]:
        """Get controllers information."""
        adapters = get_adapters_from_lsdev(**params)
        
        controllers = []
        for adapter in adapters:
            controllers.append({
                'NAME': adapter.get('NAME'),
            })
        
        return controllers
