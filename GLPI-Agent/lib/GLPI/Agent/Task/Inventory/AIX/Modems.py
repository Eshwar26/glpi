#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Modems - Python Implementation
"""

import re
from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.AIX import get_adapters_from_lsdev


class Modems(InventoryModule):
    """AIX Modems inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "modem"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lsdev')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        modems = Modems._get_modems(logger=logger)
        
        for modem in modems:
            if inventory:
                inventory.add_entry(
                    section='MODEMS',
                    entry=modem
                )
    
    @staticmethod
    def _get_modems(**params) -> List[Dict[str, Any]]:
        """Get modems information."""
        adapters = get_adapters_from_lsdev(**params)
        
        modems = []
        for adapter in adapters:
            description = adapter.get('DESCRIPTION', '')
            if re.search(r'modem', description, re.IGNORECASE):
                modems.append({
                    'NAME': adapter.get('NAME'),
                    'DESCRIPTION': description,
                })
        
        return modems
