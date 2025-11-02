#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux SPARC CPU - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read
from GLPI.Agent.Tools.Linux import get_cpus_from_proc


class CPU(InventoryModule):
    """SPARC CPU detection module."""
    
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
        """Parse SPARC CPU information from /proc/cpuinfo."""
        cpus_data = get_cpus_from_proc(**params)
        if not cpus_data:
            return []
        
        cpu = cpus_data[0]
        ncpus_probed = cpu.get('ncpus probed')
        if not ncpus_probed:
            return []
        
        cpus = []
        try:
            count = int(ncpus_probed)
            for _ in range(count):
                cpus.append({
                    'ARCH': 'sparc',
                    'NAME': cpu.get('cpu'),
                })
        except (ValueError, TypeError):
            pass
        
        return cpus
