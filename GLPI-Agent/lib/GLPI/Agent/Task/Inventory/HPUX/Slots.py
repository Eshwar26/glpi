#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Slots - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Slots(InventoryModule):
    """HP-UX slots detection module."""
    
    category = "slot"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ioscan')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for slot_type in ['ioa', 'ba']:
            for slot in Slots._get_slots(
                command=f"ioscan -kFC {slot_type}",
                logger=logger
            ):
                if inventory:
                    inventory.add_entry(
                        section='SLOTS',
                        entry=slot
                    )
    
    @staticmethod
    def _get_slots(**params) -> List[Dict[str, str]]:
        """Parse ioscan output for slots."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        slots = []
        for line in lines:
            info = line.split(':')
            if len(info) > 17:
                slots.append({
                    'NAME': f"{info[9]}{info[10]}",
                    'DESIGNATION': info[13],
                    'DESCRIPTION': info[17],
                })
        
        return slots
