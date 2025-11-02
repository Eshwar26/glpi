#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Memory - Python Implementation
"""

import re
from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines
from GLPI.Agent.Tools.AIX import get_lsvpd_infos


class Memory(InventoryModule):
    """AIX Memory inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "memory"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        memories = Memory._get_memories()
        for memory in memories:
            if inventory:
                inventory.add_entry(
                    section='MEMORIES',
                    entry=memory
                )
        
        # Memory informations
        # lsdev -Cc memory -F 'name' -t totmem
        # lsattr -EOlmem0
        memory_size = 0
        lsdev_lines = get_all_lines(
            command='lsdev -Cc memory -F "name" -t totmem',
            logger=logger
        )
        
        if lsdev_lines:
            for device in lsdev_lines:
                lsattr_lines = get_all_lines(
                    command=f"lsattr -EOl {device.strip()}",
                    logger=logger
                )
                if lsattr_lines:
                    for line in lsattr_lines:
                        if not line.startswith('#'):
                            # See: http://forge.fusioninventory.org/issues/399
                            # TODO: the regex should be improved here
                            match = re.match(r'^(.+):(\d+)', line)
                            if match:
                                memory_size += int(match.group(2))
        
        # Paging Space
        swap_size = None
        swap_lines = get_all_lines(command='lsps -s', logger=logger)
        if swap_lines:
            for line in swap_lines:
                if not line.startswith('Total'):
                    match = re.match(r'^\s*(\d+)\w*\s+\d+.+', line)
                    if match:
                        swap_size = int(match.group(1))
        
        if inventory:
            hardware_info = {
                'MEMORY': memory_size,
            }
            if swap_size is not None:
                hardware_info['SWAP'] = swap_size
            inventory.set_hardware(hardware_info)
    
    @staticmethod
    def _get_memories(**params) -> List[Dict[str, Any]]:
        """Get memory modules information."""
        infos = get_lsvpd_infos(**params)
        memories = []
        numslots = 0
        
        for info in infos:
            if info.get('DS') != 'Memory DIMM':
                continue
            
            memories.append({
                'DESCRIPTION': info.get('DS'),
                'CAPACITY': info.get('SZ'),
                'CAPTION': f"Slot {info.get('YL', '')}",
                'SERIALNUMBER': info.get('SN'),
                'NUMSLOTS': numslots
            })
            numslots += 1
        
        return memories
