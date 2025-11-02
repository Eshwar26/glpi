#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization systemd-nspawn - Python Implementation
"""

import os
import re
from typing import Any, Dict, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import (
    can_run,
    get_all_lines,
    get_first_line,
    get_first_match,
)
from GLPI.Agent.Tools.Linux import get_cpus_from_proc
from GLPI.Agent.Tools import get_canonical_size
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING, STATUS_OFF


class SystemdNspawn(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('machinectl') and can_run('systemctl')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        machines = SystemdNspawn._get_virtual_machines(logger=logger)
        for machine in machines:
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_virtual_machines(**params) -> List[Dict[str, Any]]:
        logger = params.get('logger')

        nspawn_lines = get_all_lines(
            command='systemctl --system --all -q --plain list-units systemd-nspawn@*',
            logger=logger,
        ) or []

        machines_index: Dict[str, Dict[str, Any]] = {}
        for line in nspawn_lines:
            m = re.match(r'^systemd-nspawn@(\S+)\.service\s+\w+\s+\w+\s+(\w+)', line)
            if not m:
                continue
            name, state = m.group(1), m.group(2)
            status = STATUS_RUNNING if state == 'running' else STATUS_OFF
            machines_index[name] = {
                'NAME': name,
                'VMTYPE': 'systemd-nspawn',
                'VCPU': 0,
                'STATUS': status,
            }

        machines: List[Dict[str, Any]] = []

        machinectl_lines = get_all_lines(
            command='machinectl --no-pager --no-legend', logger=logger
        ) or []
        for line in machinectl_lines:
            m = re.match(r'^(\S+)\s+(\w+)\s+(\S+)', line)
            if not m:
                continue
            name, class_, service = m.groups()
            if service == 'libvirt-qemu':
                continue
            if name in machines_index:
                container = machines_index.pop(name)
                container['SUBSYSTEM'] = class_
            else:
                container = {
                    'NAME': name,
                    'VMTYPE': service,
                    'SUBSYSTEM': class_,
                    'VCPU': 0,
                    'STATUS': STATUS_RUNNING,
                }
            machines.append(container)

        machines.extend(machines_index.values())

        for container in machines:
            name = container['NAME']
            uuid = None
            if container['STATUS'] == STATUS_RUNNING:
                uuid = get_first_match(
                    command=f'machinectl show -p Id {name}',
                    pattern=r'^Id=(\w+)$',
                    logger=logger,
                )
            else:
                mount = get_first_line(
                    command=f'systemctl --system show systemd-nspawn@{name}.service -P RequiresMountsFor',
                    logger=logger,
                )
                if mount and os.path.isdir(mount) and os.path.exists(f'{mount}/etc/machine-id'):
                    uuid = get_first_line(file=f'{mount}/etc/machine-id', logger=logger)
            if uuid:
                m = re.match(r'^(\w{8})(\w{4})(\w{4})(\w{4})(\w{12})$', uuid)
                if m:
                    uuid = f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}-{m.group(5)}"
                container['UUID'] = uuid

            unit_lines = get_all_lines(
                command=f'systemctl --system cat systemd-nspawn@{name}.service',
                logger=logger,
            ) or []
            for line in unit_lines:
                m_quota = re.match(r'^CPUQuota=(\d+)%', line)
                if m_quota:
                    container['VCPU'] = int(int(m_quota.group(1)) / 100)
                m_mem = re.match(r'^MemoryMax=(\d+)$', line)
                if m_mem:
                    container['MEMORY'] = get_canonical_size(m_mem.group(1) + ' bytes', 1024)

            if not container.get('VCPU'):
                cpus = get_cpus_from_proc(logger=logger)
                container['VCPU'] = len(cpus) if isinstance(cpus, list) else 0

        return machines

