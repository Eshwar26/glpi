#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization VirtualBox - Python Implementation
"""

import sys
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import (
    can_run,
    get_first_match,
    get_all_lines,
    get_first_line,
    has_folder,
)
from GLPI.Agent.Tools import compare_version, get_canonical_size
from GLPI.Agent.Tools.Virtualization import (
    STATUS_OFF,
    STATUS_CRASHED,
    STATUS_BLOCKED,
    STATUS_PAUSED,
    STATUS_RUNNING,
    STATUS_DYING,
)


class VirtualBox(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        if not can_run('VBoxManage'):
            return False

        major_minor = get_first_match(
            command='VBoxManage --version', pattern=r'^(\d)\.(\d)'
        )
        if isinstance(major_minor, (list, tuple)) and len(major_minor) == 2:
            try:
                major = int(major_minor[0])
                minor = int(major_minor[1])
            except ValueError:
                return False
            return compare_version(major, minor, 2, 1)
        return False

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        vms_command = 'VBoxManage -nologo list vms'
        for vm in VirtualBox._parse_vms(logger=logger, command=vms_command):
            machine = VirtualBox._parse_showvminfo(
                logger=logger, command=f'VBoxManage -nologo showvminfo {vm}'
            )
            if not machine:
                continue
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

        # Scan user home directories if requested and supported
        scan_homedirs = params.get('scan_homedirs')
        if not scan_homedirs:
            if logger:
                logger.info(
                    "'scan-homedirs' configuration parameters disabled, ignoring virtualbox virtual machines in user directories"
                )
            return

        if sys.platform == 'win32':
            if logger:
                logger.info(
                    'scanning of virtualbox virtual machines in user directories not supported under win32'
                )
            return

        # Build list of users with VirtualBox config directories
        users: List[str] = []
        user_vbox_folder = 'Library/VirtualBox' if sys.platform == 'darwin' else '.config/VirtualBox'

        try:
            import pwd, os
            current_uid = os.getuid()
            for u in pwd.getpwall():
                try:
                    if u.pw_uid == current_uid:
                        continue
                    home = u.pw_dir
                    if has_folder(f"{home}/{user_vbox_folder}"):
                        users.append(u.pw_name)
                except Exception:
                    continue
        except Exception:
            # Fallback: no user enumeration
            pass

        for user in users:
            vms_command = f"su '{user}' -c 'VBoxManage -nologo list vms'"
            for vm in VirtualBox._parse_vms(logger=logger, command=vms_command):
                command = f"su '{user}' -c 'VBoxManage -nologo showvminfo {vm}'"
                machine = VirtualBox._parse_showvminfo(logger=logger, command=command)
                if not machine:
                    continue
                machine['OWNER'] = user
                if inventory:
                    inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _parse_vms(**params) -> List[str]:
        vms: List[str] = []
        lines = get_all_lines(**params) or []
        import re
        for line in lines:
            m = re.match(r'^"[^"]+"\s+{([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})}$', line)
            if m:
                vms.append(m.group(1))
        return vms

    @staticmethod
    def _parse_showvminfo(**params) -> Optional[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        if not lines:
            return None

        machines: List[Dict[str, Any]] = []
        machine: Optional[Dict[str, Any]] = None
        index: Optional[int] = None
        import re

        status_list = {
            'powered off': STATUS_OFF,
            'saved': STATUS_OFF,
            'teleported': STATUS_OFF,
            'aborted': STATUS_CRASHED,
            'stuck': STATUS_BLOCKED,
            'teleporting': STATUS_PAUSED,
            'live snapshotting': STATUS_RUNNING,
            'starting': STATUS_RUNNING,
            'stopping': STATUS_DYING,
            'saving': STATUS_DYING,
            'restoring': STATUS_RUNNING,
            'running': STATUS_RUNNING,
            'paused': STATUS_PAUSED,
        }

        for line in lines:
            m_name = re.match(r'^Name:\s+(.*)$', line)
            if m_name:
                if index is not None:
                    index = None
                    continue
                if machine:
                    machines.append(machine)
                machine = {
                    'NAME': m_name.group(1),
                    'VCPU': 1,
                    'SUBSYSTEM': 'Oracle VM VirtualBox',
                    'VMTYPE': 'virtualbox',
                }
                continue

            if machine is None:
                continue

            m_uuid = re.match(r'^UUID:\s+(.+)', line)
            if m_uuid:
                machine['UUID'] = m_uuid.group(1)
                continue

            m_mem = re.match(r'^Memory size:\s+(.+)', line)
            if m_mem:
                machine['MEMORY'] = get_canonical_size(m_mem.group(1))
                continue

            m_state = re.match(r'^State:\s+(.+) \(', line)
            if m_state:
                machine['STATUS'] = status_list.get(m_state.group(1))
                continue

            m_index = re.match(r'^Index:\s+(\d+)$', line)
            if m_index:
                index = int(m_index.group(1))
                continue

        if machine:
            machines.append(machine)

        # Return first machine; showvminfo prints a single VM description per call
        return machines[0] if machines else None

