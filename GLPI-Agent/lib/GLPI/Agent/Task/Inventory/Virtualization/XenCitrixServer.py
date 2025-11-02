#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Xen Citrix Server - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class XenCitrixServer(InventoryModule):
    runMeIfTheseChecksFailed = ['GLPI::Agent::Task::Inventory::Virtualization::Libvirt']

    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('xe')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        machines = XenCitrixServer._get_virtual_machines(command='xe vm-list', logger=logger)
        for machine in machines:
            extended = XenCitrixServer._get_virtual_machine(
                command=f"xe vm-param-list uuid={machine['UUID']}", logger=logger
            )
            if not extended:
                continue
            machine.update(extended)
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_virtual_machines(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        machines: List[Dict[str, Any]] = []
        for line in lines:
            m = re.search(r'uuid *\( *RO\) *: *([-0-9a-f]+) *$', line)
            if not m:
                continue
            uuid = m.group(1)
            machines.append({'UUID': uuid, 'SUBSYSTEM': 'xe', 'VMTYPE': 'xen'})
        return machines

    @staticmethod
    def _get_virtual_machine(**params) -> Optional[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        if not lines:
            return None
        machine: Dict[str, Any] = {}
        for line in lines:
            m = re.match(r'^\s*(\S+)\s*\(...\)\s*:\s*(.*)$', line)
            if not m:
                continue
            label, value = m.groups()
            if label == 'dom-id' and value.isdigit() and int(value) == 0:
                return None
            if label == 'name-label':
                machine['NAME'] = value
            elif label == 'memory-actual':
                try:
                    machine['MEMORY'] = int(int(value) / 1048576)
                except Exception:
                    pass
            elif label == 'power-state':
                machine['STATUS'] = 'running' if value == 'running' else ('shutdown' if value == 'halted' else 'off')
            elif label == 'VCPUs-number':
                machine['VCPU'] = value
            elif label == 'name-description':
                if value:
                    machine['COMMENT'] = value
        return machine if machine else None

