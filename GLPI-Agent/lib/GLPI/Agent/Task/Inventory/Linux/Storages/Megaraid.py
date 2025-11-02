#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages Megaraid - Python Implementation

Authors: Egor Shornikov <se@wbr.su>, Egor Morozov <akrus@flygroup.st>
License: GPLv2+
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Megaraid(InventoryModule):
    """LSI Megaraid controller inventory using megasasctl."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('megasasctl')
    
    @staticmethod
    def _parse_megasasctl(**params) -> List[Dict[str, Any]]:
        """Parse megasasctl output."""
        lines = get_all_lines(command='megasasctl -v', **params)
        if not lines:
            return []
        
        storages = []
        for line in lines:
            match = re.match(r'\s*([a-z]\d[a-z]\d+[a-z]\d+)\s+(\S+)\s+(\S+)\s*(\S+)\s+\S+\s+\S+\s*', line)
            if not match:
                continue
            
            disk_addr, vendor, model, size = match.groups()
            
            # Convert size from GiB to MB
            size_match = re.match(r'(\d+)GiB', size)
            if size_match:
                size = int(size_match.group(1)) * 1024
            
            storage = {
                'NAME': disk_addr,
                'MANUFACTURER': vendor,
                'MODEL': model,
                'DESCRIPTION': 'SAS',
                'TYPE': 'disk',
                'DISKSIZE': size
            }
            
            storages.append(storage)
        
        return storages
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        for storage in Megaraid._parse_megasasctl(**params):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=storage)
