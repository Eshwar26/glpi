#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Storages Megaraid - Python Implementation

Authors: Egor Shornikov <se@wbr.su>, Egor Morozov <akrus@flygroup.st>
License: GPLv2+
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Megaraid(InventoryModule):
    """BSD Megaraid storage inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('mfiutil')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        storages = Megaraid._parse_mfiutil(
            logger=logger,
            command='mfiutil show drives'
        )
        
        for storage in storages:
            if inventory:
                inventory.add_entry(section='STORAGES', entry=storage)
    
    @staticmethod
    def _parse_mfiutil(**params) -> List[Dict[str, Any]]:
        """Parse mfiutil output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        storages = []
        for line in lines:
            # Format: name(size) type <vendor model serial=serial> status
            match = re.match(
                r'^[^(]*\(\s+(\d+\w+)\)\s+\S+\s+<(\S+)\s+(\S+)\s+\S+\s+serial=(\S+)>\s+(\S+)\s+.*$',
                line
            )
            if not match:
                continue
            
            size_str, vendor, model, serial, storage_type = match.groups()
            
            # Convert size to MB
            size = 0
            if re.match(r'(\d+)G', size_str):
                size_match = re.match(r'(\d+)G', size_str)
                if size_match:
                    size = int(size_match.group(1)) * 1024
            elif re.match(r'(\d+)T', size_str):
                size_match = re.match(r'(\d+)T', size_str)
                if size_match:
                    size = int(size_match.group(1)) * 1024 * 1024
            
            storage = {
                'NAME': f"{vendor} {model}",
                'DESCRIPTION': storage_type,
                'TYPE': 'disk',
                'DISKSIZE': size,
                'SERIALNUMBER': serial,
            }
            
            storages.append(storage)
        
        return storages
