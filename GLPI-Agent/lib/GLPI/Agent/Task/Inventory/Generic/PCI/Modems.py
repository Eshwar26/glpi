#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic PCI Modems - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_pci_devices


class Modems(InventoryModule):
    """PCI modems inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "modem"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
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
    def _get_modems(**params) -> List[Dict[str, str]]:
        """Get PCI modems."""
        modems = []
        
        for device in get_pci_devices(**params):
            if not device.get('NAME'):
                continue
            if not re.search(r'modem', device['NAME'], re.IGNORECASE):
                continue
            
            modems.append({
                'DESCRIPTION': device['NAME'],
                'NAME': device.get('MANUFACTURER'),
            })
        
        return modems
