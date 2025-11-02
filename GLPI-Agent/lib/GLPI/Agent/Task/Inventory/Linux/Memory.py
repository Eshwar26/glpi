#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Memory - Python Implementation
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_all_lines, first


class Memory(InventoryModule):
    """Linux memory detection module."""
    
    category = "memory"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/meminfo')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        lines = get_all_lines(
            file='/proc/meminfo',
            logger=params.get('logger')
        )
        
        memory_line = first(lambda l: re.match(r'^MemTotal:\s*(\d+)', l), lines)
        swap_line = first(lambda l: re.match(r'^SwapTotal:\s*(\d+)', l), lines)
        
        hw = {}
        if memory_line:
            match = re.search(r'(\d+)', memory_line)
            if match:
                hw['MEMORY'] = int(int(match.group(1)) / 1024)
        
        if swap_line:
            match = re.search(r'(\d+)', swap_line)
            if match:
                hw['SWAP'] = int(int(match.group(1)) / 1024)
        
        if inventory:
            inventory.set_hardware(hw)
