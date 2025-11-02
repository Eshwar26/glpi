#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Hpvm - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING, STATUS_OFF, STATUS_CRASHED
from GLPI.Agent.XML import XML


class Hpvm(InventoryModule):
    """HP-UX Virtual Machines detection module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('hpvmstatus')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for machine in Hpvm._get_machines(
            command='hpvmstatus -X',
            logger=logger
        ):
            if inventory:
                inventory.add_entry(
                    section='VIRTUALMACHINES',
                    entry=machine
                )
    
    @staticmethod
    def _get_machines(**params) -> List[Dict[str, Any]]:
        """Get virtual machines from hpvmstatus."""
        xml_data = get_all_lines(**params)
        if not xml_data:
            return []
        
        data = XML(string='\n'.join(xml_data)).dump_as_hash()
        mvs = data.get('pman', {}).get('virtual_machine')
        if not mvs:
            return []
        
        units = {
            'MB': 1,
            'GB': 1024
        }
        
        status_map = {
            'On': STATUS_RUNNING,
            'Off': STATUS_OFF,
            'Invalid': STATUS_CRASHED
        }
        
        machines = []
        for name, info in mvs.items():
            memory_data = info.get('memory', {}).get('total', {})
            memory = memory_data.get('content', 0) * units.get(memory_data.get('unit', 'MB'), 1)
            
            machine = {
                'MEMORY': memory,
                'NAME': name,
                'UUID': info.get('uuid'),
                'STATUS': status_map.get(info.get('vm_state'), STATUS_OFF),
                'SUBSYSTEM': 'HPVM',
                'VMTYPE': 'HPVM',
                'VCPU': info.get('vcpu_number')
            }
            
            machines.append(machine)
        
        return machines
