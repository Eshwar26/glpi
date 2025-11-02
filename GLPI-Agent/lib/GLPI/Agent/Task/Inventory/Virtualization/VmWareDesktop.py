#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization VMware Desktop - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, has_file


class VmWareDesktop(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('/Library/Application Support/VMware Fusion/vmrun') or can_run('vmrun')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        command = 'vmrun list' if can_run('vmrun') else "'/Library/Application Support/VMware Fusion/vmrun' list"
        for machine in VmWareDesktop._get_machines(command=command, logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_machines(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        if not lines:
            return []
        # skip first line
        lines = lines[1:]

        machines: List[Dict[str, Any]] = []
        logger = params.get('logger')
        for line in lines:
            path = line.strip()
            if not path or not has_file(path):
                continue
            info = VmWareDesktop._get_machine_info(file=path, logger=logger)
            if not info:
                continue
            machines.append({
                'NAME': info.get('displayName'),
                'VCPU': 1,
                'UUID': info.get('uuid.bios'),
                'MEMORY': info.get('memsize'),
                'STATUS': 'running',
                'SUBSYSTEM': 'VmWare Fusion',
                'VMTYPE': 'VmWare',
            })
        return machines

    @staticmethod
    def _get_machine_info(**params) -> Optional[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        if not lines:
            return None
        info: Dict[str, Any] = {}
        import re
        for line in lines:
            m = re.match(r'^(\S+)\s*=\s*(\S+.*)', line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            value = value.strip('"')
            info[key] = value
        return info

