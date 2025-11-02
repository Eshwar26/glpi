#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Vserver - Python Implementation
"""

import os
import re
from typing import Any, Dict, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import (
    can_run,
    get_all_lines,
    get_first_line,
    has_folder,
    get_directory_handle,
)
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING, STATUS_OFF


class Vserver(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('vserver')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        for machine in Vserver._get_machines(command='vserver-info', logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_machines(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        util_vserver = None
        cfg_dir = None
        for line in lines:
            m_cfg = re.match(r'^\s+cfg-Directory:\s+(.*)$', line)
            if m_cfg:
                cfg_dir = m_cfg.group(1)
            m_util = re.match(r'^\s+util-vserver:\s+(.*)$', line)
            if m_util:
                util_vserver = m_util.group(1)

        if not cfg_dir or not has_folder(cfg_dir):
            return []

        handle = get_directory_handle(directory=cfg_dir, logger=params.get('logger'))
        if not handle:
            return []

        machines: List[Dict[str, Any]] = []
        try:
            for name in handle:
                if name.startswith('.') or not name.strip():
                    continue

                line = get_first_line(command=f'vserver {name} status')
                status = (
                    STATUS_OFF if (line and 'is stopped' in line) else
                    STATUS_RUNNING if (line and 'is running' in line) else
                    None
                )

                machines.append({
                    'NAME': name,
                    'STATUS': status,
                    'SUBSYSTEM': util_vserver,
                    'VMTYPE': 'vserver',
                })
        finally:
            # iterator returned by get_directory_handle may not be a real handle; nothing to close
            pass

        return machines

