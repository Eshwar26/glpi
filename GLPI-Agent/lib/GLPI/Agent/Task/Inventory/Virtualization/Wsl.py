#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization WSL - Python Implementation
"""

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, has_file, has_folder, get_all_lines
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING


class Wsl(InventoryModule):
    # Maintain runAfterIfEnabled behavior from Perl
    runAfterIfEnabled = [
        'GLPI::Agent::Task::Inventory::Win32::Hardware',
        'GLPI::Agent::Task::Inventory::Win32::CPU',
    ]

    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return sys.platform == 'win32' and can_run('wsl')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        for machine in Wsl._get_users_wsl_instances(inventory=inventory, logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_users_wsl_instances(**params) -> List[Dict[str, Any]]:
        inventory = params.get('inventory')
        logger = params.get('logger')
        machines: List[Dict[str, Any]] = []

        # Defer Win32 imports to runtime
        try:
            from GLPI.Agent.Tools.Win32 import get_wmi_objects, load_user_hive, get_registry_key, cleanup_privileges
            from GLPI.Agent.Tools.Win32.Users import getSystemUserProfiles, getProfileUsername
        except ImportError:
            return []

        cpus = getattr(inventory, 'getSection', lambda *_: [{}])('CPUS') or [{}]
        vcpu = 0
        for cpu in cpus:
            vcpu += cpu.get('CORE', 1)
        memory = getattr(inventory, 'getHardware', lambda *_: None)('MEMORY')

        os_obj = None
        for obj in get_wmi_objects(class_name='Win32_OperatingSystem', properties=['Version']):
            os_obj = obj
            break
        kernel_version = (os_obj or {}).get('Version', '')
        m_build = re.match(r'^\d+\.\d+\.(\d+)', kernel_version)
        build = int(m_build.group(1)) if m_build else None

        for user in getSystemUserProfiles():
            sid = user.get('SID')
            lxsskey = None
            userhive = None
            if not user.get('LOADED'):
                ntuserdat = f"{user.get('PATH')}/NTUSER.DAT"
                userhive = load_user_hive(sid=sid, file=ntuserdat)

            lxsskey = get_registry_key(
                path=f"HKEY_USERS/{sid}/SOFTWARE/Microsoft/Windows/CurrentVersion/Lxss/",
                required=['BasePath', 'DistributionName'],
            )
            if not lxsskey:
                continue

            usermem, uservcpu = None, None
            wslconfig = f"{user.get('PATH')}/.wslconfig"
            if has_file(wslconfig):
                usermem, uservcpu = Wsl._parse_wsl_config(file=wslconfig, logger=logger)

            for sub in list(lxsskey.keys()):
                if not re.match(r'^\{........-....-....-....-............\}/$', sub):
                    continue
                basepath = lxsskey[sub].get('/BasePath')
                distro = lxsskey[sub].get('/DistributionName')
                if not basepath or not distro:
                    continue
                username = getProfileUsername(user)
                hostname = f"{distro} on {username} account" if username else f"{distro} on {sid} profile"

                # Create an UUID derived from SID and distro name
                uuid = Wsl._uuid_from_name(f"{sid}/{distro}")

                version = '1' if has_folder(f"{basepath}/rootfs/etc") else '2'

                maxmemory = memory
                maxvcpu = vcpu
                if version == '2':
                    if uservcpu:
                        maxvcpu = uservcpu
                    if usermem:
                        maxmemory = usermem
                    elif build and build < 20175:
                        maxmemory = int(0.8 * (memory or 0)) if memory else None
                    else:
                        maxmemory = int(0.5 * (memory or 0)) if memory else None
                        if maxmemory and maxmemory > 8192:
                            maxmemory = 8192

                machines.append({
                    'NAME': hostname,
                    'VMTYPE': f"WSL{version}",
                    'SUBSYSTEM': 'WSL',
                    'VCPU': maxvcpu,
                    'MEMORY': maxmemory,
                    'UUID': uuid,
                })

            if userhive:
                cleanup_privileges()

        return machines

    @staticmethod
    def _parse_wsl_config(**params) -> Tuple[Optional[int], Optional[int]]:
        lines = get_all_lines(**params) or []
        memory = None
        vcpu = None
        wsl2 = False
        for line in lines:
            m_sec = re.match(r'^\[(.*)\]', line)
            if m_sec:
                wsl2 = m_sec.group(1).strip().lower() == 'wsl2'
                continue
            if not wsl2:
                continue
            m_mem = re.match(r'^memory\s*=\s*(\S+)', line)
            if m_mem:
                size = m_mem.group(1)
                # add B suffix if missing
                if not re.search(r'b$', size, re.I):
                    size += 'B'
                from GLPI.Agent.Tools import get_canonical_size as _gcs
                memory = _gcs(size, 1024)
                continue
            m_cpu = re.match(r'^processors\s*=\s*(\d+)', line)
            if m_cpu:
                vcpu = int(m_cpu.group(1))
        return memory, vcpu

    @staticmethod
    def _uuid_from_name(name: str) -> str:
        import hashlib
        # Upper-case hex to match Perl uc(create_uuid_from_name(...)) semantics
        return hashlib.sha1(name.encode('utf-8')).hexdigest().upper()

