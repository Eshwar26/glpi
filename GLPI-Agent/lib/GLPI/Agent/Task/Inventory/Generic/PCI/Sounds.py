#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic PCI Sounds - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_pci_devices


class Sounds(InventoryModule):
    """PCI sound cards inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "sound"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        sounds = Sounds._get_sounds(logger=logger)
        
        for sound in sounds:
            if inventory:
                inventory.add_entry(
                    section='SOUNDS',
                    entry=sound
                )
    
    @staticmethod
    def _get_sounds(**params) -> List[Dict[str, str]]:
        """Get PCI sound cards."""
        sounds = []
        
        for device in get_pci_devices(**params):
            if not device.get('NAME'):
                continue
            if not re.search(r'audio', device['NAME'], re.IGNORECASE):
                continue
            
            sound = {
                'NAME': device['NAME'],
                'MANUFACTURER': device.get('MANUFACTURER'),
            }
            
            if device.get('REV'):
                sound['DESCRIPTION'] = f"rev {device['REV']}"
            
            sounds.append(sound)
        
        return sounds
