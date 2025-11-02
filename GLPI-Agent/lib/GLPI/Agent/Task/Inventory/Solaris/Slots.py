#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Slots - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run
from GLPI.Agent.Tools.Solaris import get_prtdiag_infos


class Slots(InventoryModule):
    """Solaris slots detection module."""
    
    category = "slot"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('prtdiag')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for slot in Slots._get_slots(logger=logger):
            if inventory:
                inventory.add_entry(
                    section='SLOTS',
                    entry=slot
                )
    
    @staticmethod
    def _get_slots(**params):
        """Get slots from prtdiag."""
        info = get_prtdiag_infos(**params)
        
        if info and info.get('slots'):
            return info['slots']
        return []
