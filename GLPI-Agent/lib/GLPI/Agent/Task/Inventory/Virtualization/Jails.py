#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Jails - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING


class Jails(InventoryModule):
    """BSD Jails detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('jls')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for machine in Jails._get_virtual_machines(logger=logger):
            if inventory:
                inventory.add_entry(
                    section='VIRTUALMACHINES',
                    entry=machine
                )
    
    @staticmethod
    def _get_virtual_machines(**params) -> List[Dict[str, Any]]:
        """Get BSD jails."""
        if 'command' not in params:
            params['command'] = 'jls -n'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        machines = []
        for line in lines:
            info = {}
            for item in line.split():
                if '=' in item:
                    key, value = item.split('=', 1)
                    info[key] = value
            
            if info.get('host.hostname'):
                machine = {
                    'VMTYPE': 'bsdjail',
                    'NAME': info['host.hostname'],
                    'STATUS': STATUS_RUNNING
                }
                
                machines.append(machine)
        
        return machines
