#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux ARM CPU - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read
from GLPI.Agent.Tools.Linux import get_cpus_from_proc


class CPU(InventoryModule):
    """ARM CPU detection module."""
    
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
        """Parse ARM CPU information from /proc/cpuinfo."""
        cpus = []
        
        # https://github.com/joyent/libuv/issues/812
        for cpu in get_cpus_from_proc(**params):
            arch = 'arm'
            cpu_arch = cpu.get('cpu architecture', '')
            if cpu_arch:
                import re
                match = re.match(r'^(\d+)', cpu_arch)
                if match and int(match.group(1)) >= 8:
                    arch = 'aarch64'
            
            cpus.append({
                'ARCH': arch,
                'NAME': cpu.get('model name') or cpu.get('processor')
            })
        
        return cpus
