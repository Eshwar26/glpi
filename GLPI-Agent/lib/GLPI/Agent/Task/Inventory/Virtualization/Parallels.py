#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Parallels - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines
from GLPI.Agent.Tools.Virtualization import (
    STATUS_RUNNING, STATUS_BLOCKED, STATUS_PAUSED,
    STATUS_CRASHED, STATUS_DYING, STATUS_OFF,
)


class Parallels(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('prlctl')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        if not params.get('scan_homedirs'):
            if logger:
                logger.warning(
                    "'scan-homedirs' configuration parameter disabled, ignoring parallels virtual machines in user directories"
                )
            return

        # Enumerate macOS users by scanning /Users/* (parallels is macOS-only)
        lines = get_all_lines(command="ls -1 /Users") or []
        for user in lines:
            user = user.strip()
            if not user or user.lower() == 'shared' or user.startswith('.') or ' ' in user or "'" in user:
                continue

            for machine in Parallels._parse_prlctl_a(
                logger=logger,
                command=f"su '{user}' -c 'prlctl list -a'",
            ):
                uuid = machine.get('UUID', '')
                uuid = re.sub(r"[^A-Za-z0-9\.\s_-]", "", uuid)

                mem, vcpu = Parallels._parse_prlctl_i(
                    logger=logger,
                    command=f"su '{user}' -c 'prlctl list -i {uuid}'",
                )
                machine['MEMORY'] = mem
                machine['VCPU'] = vcpu

                if inventory:
                    inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _parse_prlctl_a(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        if not lines:
            return []

        status_list = {
            'running': STATUS_RUNNING,
            'blocked': STATUS_BLOCKED,
            'paused': STATUS_PAUSED,
            'suspended': STATUS_PAUSED,
            'crashed': STATUS_CRASHED,
            'dying': STATUS_DYING,
            'stopped': STATUS_OFF,
        }

        # drop header line
        lines = lines[1:]

        machines: List[Dict[str, Any]] = []
        for line in lines:
            info = re.split(r"\s+", line, maxsplit=3)
            if len(info) < 4:
                continue
            uuid, status_raw, _, name = info
            uuid = re.sub(r"^{(.*)}$", r"\1", uuid)
            # Avoid shell injection strings
            if re.search(r"(;\||&)", uuid):
                continue
            machines.append({
                'NAME': name,
                'UUID': uuid,
                'STATUS': status_list.get(status_raw, STATUS_OFF),
                'SUBSYSTEM': 'Parallels',
                'VMTYPE': 'parallels',
            })
        return machines

    @staticmethod
    def _parse_prlctl_i(**params) -> (Optional[int], Optional[int]):
        lines = get_all_lines(**params) or []
        mem = None
        cpus = None
        for line in lines:
            m_mem = re.match(r"^\s\smemory\s(.*)Mb", line)
            if m_mem:
                try:
                    mem = int(m_mem.group(1))
                except ValueError:
                    pass
            m_cpu = re.match(r"^\s\scpu\s(\d{1,2})", line)
            if m_cpu:
                try:
                    cpus = int(m_cpu.group(1))
                except ValueError:
                    pass
        return mem, cpus

