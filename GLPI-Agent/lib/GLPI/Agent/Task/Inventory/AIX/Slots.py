#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Slots - Python Implementation
"""

from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.AIX import get_lsvpd_infos


class Slots(InventoryModule):
    """AIX Slots inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "slot"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lsdev')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        slots = Slots._get_slots(
            command='lsdev -Cc bus -F "name:description"',
            logger=logger
        )
        
        for slot in slots:
            if inventory:
                inventory.add_entry(
                    section='SLOTS',
                    entry=slot
                )
    
    @staticmethod
    def _get_slots(**params) -> List[Dict[str, Any]]:
        """Get slots information."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        # index description by AX field from VPD infos
        logger = params.get('logger')
        infos = get_lsvpd_infos(logger=logger)
        
        description_map = {}
        for info in infos:
            ax = info.get('AX')
            yl = info.get('YL')
            if ax and yl:
                description_map[ax] = yl
        
        slots = []
        for line in lines:
            parts = line.split(':', 2)
            if len(parts) >= 2:
                name = parts[0]
                designation = parts[1]
                description = parts[2] if len(parts) > 2 else None
                
                # Use description from VPD if not present
                if name and not description and name in description_map:
                    description = description_map[name]
                
                if name and designation and description:
                    slots.append({
                        'NAME': name,
                        'DESIGNATION': designation,
                        'DESCRIPTION': description,
                    })
        
        return slots
