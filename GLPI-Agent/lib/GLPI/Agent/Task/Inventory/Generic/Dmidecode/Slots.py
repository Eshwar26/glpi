#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Slots - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.Generic import get_dmidecode_infos


class Slots(InventoryModule):
    """Dmidecode slots inventory module."""
    
    STATUS_MAP = {
        'Unknown': None,
        'In Use': 'used',
        'Available': 'free'
    }
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "slot"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        slots = Slots._get_slots(logger=logger)
        
        if not slots:
            return
        
        for slot in slots:
            if inventory:
                inventory.add_entry(
                    section='SLOTS',
                    entry=slot
                )
    
    @staticmethod
    def _get_slots(**params) -> Optional[List[Dict[str, Optional[str]]]]:
        """Get slots from dmidecode."""
        infos = get_dmidecode_infos(**params)
        
        if not infos or not infos.get(9):
            return None
        
        slots = []
        for info in infos[9]:
            slot = {
                'DESCRIPTION': info.get('Type'),
                'DESIGNATION': info.get('ID'),
                'NAME': info.get('Designation'),
                'STATUS': Slots.STATUS_MAP.get(info.get('Current Usage')) if info.get('Current Usage') else None,
            }
            slots.append(slot)
        
        return slots
