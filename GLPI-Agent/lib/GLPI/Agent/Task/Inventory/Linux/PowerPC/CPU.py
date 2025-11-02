#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux PowerPC CPU - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read
from GLPI.Agent.Tools.Linux import get_cpus_from_proc


class CPU(InventoryModule):
    """PowerPC CPU detection module."""
    
    category = "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/cpuinfo')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for cpu in CPU._get_cpus_from_proc(logger=logger, file='/proc/cpuinfo'):
            if inventory:
                inventory.add_entry(section='CPUS', entry=cpu)
    
    @staticmethod
    def _get_cpus_from_proc(**params) -> List[Dict[str, Any]]:
        """Parse PowerPC CPU information from /proc/cpuinfo."""
        cpus = []
        for cpu in get_cpus_from_proc(**params):
            speed = None
            clock = cpu.get('clock', '')
            if clock:
                match = re.search(r'(\d+)', clock)
                if match:
                    speed = int(match.group(1))
            
            manufacturer = None
            machine = cpu.get('machine', '')
            if machine and 'IBM' in machine:
                manufacturer = 'IBM'
            
            cpus.append({
                'ARCH': 'powerpc',
                'NAME': cpu.get('cpu'),
                'MANUFACTURER': manufacturer,
                'SPEED': speed
            })
        
        return cpus
