#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Softwares - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Softwares(InventoryModule):
    """HP-UX software packages detection module."""
    
    category = "software"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('swlist')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        software_list = Softwares._get_softwares_list(
            command='swlist',
            logger=logger
        )
        
        if not software_list:
            return
        
        for software in software_list:
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=software
                )
    
    @staticmethod
    def _get_softwares_list(**params) -> Optional[List[Dict[str, str]]]:
        """Parse swlist output."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        softwares = []
        for line in lines:
            match = re.match(
                r'^\s\s'       # two spaces
                r'(\S+)\s+'    # name
                r'(\S+)\s+'    # version
                r'(\S.*\S)',   # comment
                line
            )
            if not match:
                continue
            
            name = match.group(1)
            # Skip patches (start with PH)
            if name.startswith('PH'):
                continue
            
            softwares.append({
                'NAME': name,
                'VERSION': match.group(2),
                'COMMENTS': match.group(3),
                'PUBLISHER': 'HP'
            })
        
        return softwares
