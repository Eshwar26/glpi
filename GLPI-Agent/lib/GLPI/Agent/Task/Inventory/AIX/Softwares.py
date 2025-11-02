#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Softwares - Python Implementation
"""

import re
from typing import Dict, Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Softwares(InventoryModule):
    """AIX Softwares inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "software"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lslpp')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        softwares = Softwares._get_softwares_list(
            command='lslpp -c -l',
            logger=logger
        )
        
        if not softwares:
            return
        
        for software in softwares:
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=software
                )
    
    @staticmethod
    def _get_softwares_list(**params) -> Optional[List[Dict[str, Any]]]:
        """Get softwares list."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        # skip headers
        if lines:
            lines = lines[1:]
        
        softwares = []
        for line in lines:
            entry = line.split(':')
            if len(entry) < 7:
                continue
            
            # Skip device entries
            if re.match(r'^device', entry[1]):
                continue
            
            # Strip trailing whitespace from comments
            comments = entry[6].rstrip()
            
            softwares.append({
                'COMMENTS': comments,
                'FOLDER': entry[0],
                'NAME': entry[1],
                'VERSION': entry[2],
            })
        
        return softwares
