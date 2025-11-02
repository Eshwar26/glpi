#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Sounds - Python Implementation
"""

import re
from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.AIX import get_adapters_from_lsdev


class Sounds(InventoryModule):
    """AIX Sounds inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "sound"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lsdev')
    
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
    def _get_sounds(**params) -> List[Dict[str, Any]]:
        """Get sound devices information."""
        adapters = get_adapters_from_lsdev(**params)
        
        sounds = []
        for adapter in adapters:
            description = adapter.get('DESCRIPTION', '')
            if re.search(r'audio', description, re.IGNORECASE):
                sounds.append({
                    'NAME': adapter.get('NAME'),
                    'DESCRIPTION': description
                })
        
        return sounds
