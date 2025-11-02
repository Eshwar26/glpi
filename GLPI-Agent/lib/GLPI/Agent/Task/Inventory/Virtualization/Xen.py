#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Xen - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines, get_first_match, can_run
from GLPI.Agent.Tools.Virtualization import (
    STATUS_RUNNING, STATUS_BLOCKED, STATUS_PAUSED,
    STATUS_SHUTDOWN, STATUS_CRASHED, STATUS_DYING, STATUS_OFF,
)


class Xen(InventoryModule):
    # Keep same dependency behavior as Perl
    runMeIfTheseChecksFailed = [
        'GLPI::Agent::Task::Inventory::Virtualization::Libvirt',
        'GLPI::Agent::Task::Inventory::Virtualization::XenCitrixServer',
    ]

    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('xm') or can_run('xl')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        toolstack, list_param = 'xm', '-l'
        lines = get_all_lines(command='xm list', logger=logger) or []
        if not lines:
            toolstack, list_param = 'xl', '-v'
            lines = get_all_lines(command='xl list', logger=logger) or []
        if not lines:
            return

        if logger:
            logger.info(f"Xen {toolstack} toolstack detected")

        for machine in Xen._get_virtual_machines(lines=lines, logger=logger, command=f'{toolstack} list'):
            machine['SUBSYSTEM'] = toolstack
            uuid = Xen._get_uuid(command=f"{toolstack} list {list_param} {machine['NAME']}", logger=logger)
            machine['UUID'] = uuid
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)
            if logger:
                logger.debug(f"{machine['NAME']}: [{uuid}]")

    @staticmethod
    def _get_uuid(**params) -> Optional[str]:
        return get_first_match(pattern=r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', **params)

    @staticmethod
    def _get_virtual_machines(**params) -> List[Dict[str, Any]]:
        lines = params.get('lines') or []
        logger = params.get('logger')
        command = params.get('command')

        if not lines:
            return []

        status_list = {
            'r': STATUS_RUNNING,
            'b': STATUS_BLOCKED,
            'p': STATUS_PAUSED,
            's': STATUS_SHUTDOWN,
            'c': STATUS_CRASHED,
            'd': STATUS_DYING,
        }

        # drop headers
        lines = lines[1:]

        machines: List[Dict[str, Any]] = []
        import re
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            name = memory = vcpu = status = None
            vmid = None

            if len(parts) == 4:
                name, memory, vcpu = parts
                status = STATUS_OFF
            else:
                m = re.match(r"^(.*\S)\s+(\d+)\s+(\d+)\s+(\d+)\s+([a-z-]{5,6})\s", line)
                if m:
                    name, vmid, memory, vcpu, status_str = m.groups()
                    status_key = status_str.replace('-', '') if status_str else ''
                    status = status_list.get(status_key, STATUS_OFF)
                    try:
                        if int(vmid) == 0:
                            continue
                    except ValueError:
                        pass
                else:
                    if logger:
                        msg = "_get_virtual_machines(): unrecognized output"
                        if command:
                            msg += f" for command '{command}'"
                        msg += f": {line}"
                        logger.error(msg)
                    continue

            if name == 'Domain-0':
                continue

            machines.append({
                'MEMORY': memory,
                'NAME': name,
                'STATUS': status,
                'SUBSYSTEM': 'xm',
                'VMTYPE': 'xen',
                'VCPU': vcpu,
            })

        return machines

