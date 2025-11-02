#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization VMware ESX - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, has_file, get_first_match


class VmWareESX(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('vmware-cmd')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        for machine in VmWareESX._get_machines(command='vmware-cmd -l', logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_machines(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        logger = params.get('logger')
        machines: List[Dict[str, Any]] = []
        for line in lines:
            path = line.strip()
            if not path or not has_file(path):
                continue
            info = VmWareESX._get_machine_info(file=path, logger=logger)
            if not info:
                continue
            machine = {
                'MEMORY': info.get('memsize'),
                'NAME': info.get('displayName'),
                'UUID': info.get('uuid.bios'),
                'SUBSYSTEM': 'VmWareESX',
                'VMTYPE': 'VmWare',
            }
            status = get_first_match(
                command=f"vmware-cmd '{path}' getstate",
                logger=logger,
                pattern=r'= (\w+)',
            ) or 'unknown'
            machine['STATUS'] = status

            if machine['UUID']:
                uuid = re.sub(r'\s+', '', machine['UUID'])
                m = re.match(r'^(........)(....)(....)-(....)(.+)$', uuid)
                if m:
                    uuid = f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}-{m.group(5)}"
                machine['UUID'] = uuid

            machines.append(machine)
        return machines

    @staticmethod
    def _get_machine_info(**params) -> Optional[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        if not lines:
            return None
        info: Dict[str, Any] = {}
        for line in lines:
            m = re.match(r'^(\S+)\s*=\s*(\S+.*)', line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            value = re.sub(r'^(\"|\")|((\"|\"))$', '', value).strip('"')
            info[key] = value
        return info

