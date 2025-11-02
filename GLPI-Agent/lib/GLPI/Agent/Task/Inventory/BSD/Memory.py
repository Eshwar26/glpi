#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Memory - Python Implementation
"""

from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_first_match


class Memory(InventoryModule):
    """BSD Memory inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "memory"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('sysctl') and can_run('swapctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        # Swap
        swap_size_str = get_first_match(
            command='swapctl -sk',
            pattern=r'total:\s*(\d+)'
        )
        swap_size = int(swap_size_str) if swap_size_str else 0
        
        # RAM
        memory_size_str = get_first_line(command='sysctl -n hw.physmem')
        memory_size = int(memory_size_str) if memory_size_str else 0
        memory_size = memory_size / 1024
        
        if inventory:
            inventory.set_hardware({
                'MEMORY': int(memory_size / 1024),
                'SWAP': int(swap_size / 1024),
            })
