#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux MIPS CPU - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import has_file
from GLPI.Agent.Tools.Linux import get_cpus_from_proc


class CPU(InventoryModule):
    """MIPS CPU detection module."""
    
    category = "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return has_file('/proc/cpuinfo')
    
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
        """Parse MIPS CPU information from /proc/cpuinfo."""
        cpus = []
        for cpu in get_cpus_from_proc(**params):
            cpus.append({
                'ARCH': 'mips',
                'NAME': cpu.get('cpu model'),
            })
        
        return cpus
