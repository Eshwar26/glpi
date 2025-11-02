#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization LXD - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines, can_run, get_first_line
from GLPI.Agent.Tools.Virtualization import (
    STATUS_RUNNING, STATUS_PAUSED, STATUS_OFF, get_virtual_uuid,
)
from GLPI.Agent.Tools import get_canonical_size


class Lxd(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('lxd') and can_run('lxc')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        for machine in Lxd._get_virtual_machines(command='lxc list', logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_virtual_machine_state(**params) -> Dict[str, Any]:
        lines = get_all_lines(**params) or []
        info: Dict[str, str] = {}
        for line in lines:
            m = re.match(r'^(\S+):\s*(\S+)$', line)
            if m:
                info[m.group(1).lower()] = m.group(2)

        status_raw = info.get('status', '')
        status = (
            STATUS_RUNNING if re.match(r'^Running$', status_raw, re.I) else
            STATUS_PAUSED if re.match(r'^FROZEN$', status_raw, re.I) else
            STATUS_OFF if re.match(r'^Stopped$', status_raw, re.I) else
            status_raw
        )
        return {'VMID': info.get('pid'), 'STATUS': status}

    @staticmethod
    def _get_virtual_machine_config(**params) -> Dict[str, Any]:
        lines = get_all_lines(**params) or []
        config: Dict[str, Any] = {'VCPU': 0}
        for line in lines:
            if line.startswith('#'):
                continue
            m = re.match(r'^\s*(\S+)\s*:\s*(\S+)\s*$', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if key == 'volatile.eth0.hwaddr':
                config['MAC'] = val
            if key == 'limits.memory':
                config['MEMORY'] = get_canonical_size(val)
            elif key == 'limits.cpu':
                m_cpu = re.match(r'^"?(\d+)"?$', val)
                if m_cpu:
                    config['VCPU'] = int(m_cpu.group(1))
            if key == 'lxc.cgroup.cpuset.cpus':
                vcpu = config.get('VCPU', 0)
                for token in val.split(','):
                    r = re.match(r'^(\d+)-(\d+)$', token.strip())
                    if r:
                        vcpu += int(r.group(2)) - int(r.group(1)) + 1
                    else:
                        vcpu += 1
                config['VCPU'] = vcpu
        return config

    @staticmethod
    def _get_virtual_machines(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        logger = params.get('logger')
        machines: List[Dict[str, Any]] = []

        for line in lines:
            if re.search(r'NAME.*STATE', line):
                continue
            m = re.match(r'^\|+\s*([^| ]+)', line)
            if not m:
                continue
            name = m.group(1)

            state = Lxd._get_virtual_machine_state(command=f'lxc info {name}', logger=logger)
            config = Lxd._get_virtual_machine_config(command=f'lxc config show {name}', logger=logger)
            machineid = get_first_line(command=f'lxc file pull {name}/etc/machine-id -', logger=logger)

            machines.append({
                'NAME': name,
                'VMTYPE': 'LXD',
                'STATUS': state.get('STATUS'),
                'VCPU': config.get('VCPU'),
                'MEMORY': config.get('MEMORY'),
                'UUID': get_virtual_uuid(machineid, name),
            })

        return machines

