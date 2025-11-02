#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Qemu - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines, can_run
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING
from GLPI.Agent.Tools import get_canonical_size


class Qemu(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        # Avoid duplicated entry with libvirt
        if can_run('virsh'):
            return False
        return can_run('qemu') or can_run('kvm') or can_run('qemu-kvm')

    @staticmethod
    def _parse_process(cmd: str) -> Optional[Dict[str, Any]]:
        values: Dict[str, Any] = {}

        # Split options on ' -'
        parts = cmd.split(' -')
        if not parts:
            return None
        first = parts.pop(0)

        import re
        m = re.match(r'^(?:/usr/(s?)bin/)?(\S+)', first)
        if m:
            values['vmtype'] = 'kvm' if 'kvm' in m.group(2) else 'qemu'

        for option in parts:
            if re.match(r'^(?:[fhsv]d[a-d]|cdrom) (\S+)', option):
                if 'name' not in values:
                    values['name'] = re.sub(r'^(?:[fhsv]d[a-d]|cdrom)\s+', '', option).split()[0]
            elif re.match(r'^name ([^\s,]+)', option):
                values['name'] = re.sub(r'^name\s+', '', option).split(',')[0]
            elif re.match(r'^m .*size=(\S+)', option):
                mem = re.sub(r'^m .*size=', '', option).split(',', 1)[0]
                values['mem'] = get_canonical_size(mem)
            elif re.match(r'^m (\S+)', option):
                mem = re.sub(r'^m\s+', '', option)
                values['mem'] = get_canonical_size(mem)
            elif re.match(r'^uuid (\S+)', option):
                values['uuid'] = option.split()[1]
            elif re.match(r'^enable-kvm', option):
                values['vmtype'] = 'kvm'

            if 'smbios' in option:
                mu = re.search(r'smbios.*uuid=([a-zA-Z0-9-]+)', option)
                if mu:
                    values['uuid'] = mu.group(1)
                ms = re.search(r'smbios.*serial=([a-zA-Z0-9-]+)', option)
                if ms:
                    values['serial'] = ms.group(1)

        if 'mem' in values and isinstance(values['mem'], str) and values['mem'].isdigit() and int(values['mem']) == 0:
            values['mem'] = 128

        return values

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        # Fetch processes lines. We approximate getProcesses by using ps output.
        # We filter with regex similar to Perl filter
        lines = get_all_lines(
            command="ps -eo pid,command | grep -E '(qemu|kvm|qemu-kvm|qemu-system\\S+).*\\S' | grep -v grep",
            logger=logger,
        ) or []

        for line in lines:
            # Extract the command part after PID
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            cmd = parts[1]

            # Skip qemu guest agent
            if 'qemu-ga' in cmd:
                continue

            values = Qemu._parse_process(cmd)
            if not values:
                continue
            if not values.get('name'):
                continue

            if inventory:
                inventory.add_entry(
                    section='VIRTUALMACHINES',
                    entry={
                        'NAME': values.get('name'),
                        'UUID': values.get('uuid'),
                        'VCPU': 1,
                        'MEMORY': values.get('mem'),
                        'STATUS': STATUS_RUNNING,
                        'SUBSYSTEM': values.get('vmtype'),
                        'VMTYPE': values.get('vmtype'),
                        'SERIAL': values.get('serial'),
                    },
                )

