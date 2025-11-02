#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization LXC - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import (can_run, get_all_lines, get_first_line,
                              get_first_match, can_read)
from GLPI.Agent.Tools.Linux import get_cpus_from_proc
from GLPI.Agent.Tools.Network import mac_address_pattern
from GLPI.Agent.Tools import get_canonical_size
from GLPI.Agent.Tools.Virtualization import (
    STATUS_RUNNING, STATUS_PAUSED, STATUS_OFF,
    get_virtual_uuid,
)


class Lxc(InventoryModule):
    """LXC containers detection module (also supports Proxmox pct)."""

    @staticmethod
    def isEnabled(**params: Any) -> bool:
        return can_run('lxc-ls') or can_run('pct')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        for machine in Lxc._get_virtual_machines(
            runpct=can_run('pct'), logger=logger
        ):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_virtual_machine_state(**params) -> str:
        lines = get_all_lines(**params) or []
        state = STATUS_OFF
        for line in lines:
            if line.lower().startswith('state:'):
                value = line.split(':', 1)[1].strip().upper()
                state = (
                    STATUS_RUNNING if value == 'RUNNING' else
                    STATUS_PAUSED if value == 'FROZEN' else
                    STATUS_OFF
                )
                break
        return state

    @staticmethod
    def _get_virtual_machine(**params) -> Optional[Dict[str, Any]]:
        name = params['name']
        ctid = params.get('ctid', name)
        lxcpath = params['lxcpath']
        logger = params.get('logger')
        version = float(params.get('version') or 0)

        container: Dict[str, Any] = {
            'NAME': name,
            'VMTYPE': 'lxc',
            'VCPU': 0,
            'STATUS': Lxc._get_virtual_machine_state(
                command=params.get('test_cmdstate') or f"lxc-info -n '{ctid}' -s",
                logger=logger,
            ),
        }

        proxmox = True if ctid.isdigit() else False

        command = (
            f"lxc-info -n '{ctid}' -c lxc.cgroup.memory.limit_in_bytes "
            f"-c lxc.cgroup2.memory.max -c lxc.cgroup.cpuset.cpus -c lxc.cgroup2.cpuset.cpus"
        )
        if version < 2.1:
            command += f"; grep lxc.network.hwaddr {lxcpath}/{ctid}/config"
            if proxmox:
                command += f"; grep utsname {lxcpath}/{ctid}/config"
        else:
            command += " -c lxc.net.0.hwaddr"
            if proxmox:
                command += " -c lxc.uts.name"

        lines = get_all_lines(command=params.get('test_cmdinfo') or command, logger=logger)
        if not lines:
            return None

        import re
        for line in lines:
            if line.startswith('#'):
                continue
            m = re.match(r"^\s*(\S+)\s*=\s*(\S+)\s*$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)

            if key in ('lxc.network.hwaddr', 'lxc.net.0.hwaddr'):
                if re.match(mac_address_pattern, val, re.IGNORECASE):
                    container['MAC'] = val.lower()

            if key in ('lxc.cgroup.memory.limit_in_bytes', 'lxc.cgroup2.memory.max'):
                # Append unit for canonical size conversion
                if re.search(r"[KMGTP]$", val, re.IGNORECASE):
                    val += 'b'
                elif re.match(r"^\d+$", val):
                    val += 'bytes'
                container['MEMORY'] = get_canonical_size(val, 1024)

            if proxmox and key in ('lxc.uts.name', 'lxc.utsname'):
                container['NAME'] = val

            if key in ('lxc.cgroup.cpuset.cpus', 'lxc.cgroup2.cpuset.cpus'):
                vcpu = 0
                for token in val.split(','):
                    token = token.strip()
                    r = re.match(r"(\d+)-(\d+)", token)
                    if r:
                        vcpu += int(r.group(2)) - int(r.group(1)) + 1
                    elif token:
                        vcpu += 1
                container['VCPU'] = vcpu

        return container

    @staticmethod
    def _get_virtual_machines(**params) -> List[Dict[str, Any]]:
        logger = params.get('logger')
        runpct = params.get('runpct', False)

        lines = get_all_lines(command='pct list' if runpct else 'lxc-ls -1', logger=logger)
        if not lines:
            return []

        version = get_first_match(command='lxc-ls --version', pattern=r'^(\d+\.\d+)', logger=logger)
        try:
            version_num = float(version) if version else 0.0
        except ValueError:
            version_num = 0.0

        lxcpath = get_first_line(command='lxc-config lxc.lxcpath', logger=logger) or '/var/lib/lxc'

        rootfs_conf = 'lxc.rootfs' if version_num < 2.1 else 'lxc.rootfs.path'
        max_cpus = 0
        pct_name_offset = 0

        machines: List[Dict[str, Any]] = []

        for name in lines:
            vmid = None
            if runpct:
                import re
                m = re.match(r'^(VMID\s.*\s)Name.*$', name)
                if m:
                    pct_name_offset = len(m.group(1))
                    continue
                elif pct_name_offset:
                    m2 = re.match(r'^(\d+)', name)
                    if m2:
                        vmid = m2.group(1)
                    name = name[pct_name_offset:]
                else:
                    continue

            name = name.rstrip()
            if not name:
                continue

            ctid = vmid if (runpct and vmid) else name
            container = Lxc._get_virtual_machine(
                name=name, ctid=ctid, version=version_num, lxcpath=lxcpath, logger=logger
            )
            if not container:
                continue

            if not container.get('VCPU'):
                if not max_cpus:
                    cpus = get_cpus_from_proc(logger=logger)
                    max_cpus = len(cpus) if isinstance(cpus, list) else 0
                container['VCPU'] = max_cpus

            machineid = None
            hostname = None
            if container.get('STATUS') == STATUS_RUNNING:
                machineid = get_first_line(
                    command=f"lxc-attach -n '{ctid}' -- /bin/cat /etc/machine-id",
                    logger=logger,
                )
                hostname = get_first_line(
                    command=f"lxc-attach -n '{ctid}' -- /bin/cat /etc/hostname",
                    logger=logger,
                )
            else:
                rootfs = get_first_match(
                    command=f"/usr/bin/lxc-info -n '{ctid}' -c {rootfs_conf}",
                    pattern=r'^lxc\.rootfs.*\s*=\s*(.*)$',
                    logger=logger,
                )
                if rootfs:
                    if ':' in rootfs:
                        rootfs = rootfs.split(':', 1)[1]
                    if can_read(f"{rootfs}/etc/machine-id") and can_read(f"{rootfs}/etc/hostname"):
                        machineid = get_first_line(file=f"{rootfs}/etc/machine-id", logger=logger)
                        hostname = get_first_line(file=f"{rootfs}/etc/hostname", logger=logger)

            uuid = get_virtual_uuid(machineid, hostname)
            if uuid:
                container['UUID'] = uuid

            machines.append(container)

        return machines

