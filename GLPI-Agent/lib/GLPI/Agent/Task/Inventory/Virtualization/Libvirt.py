#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Libvirt - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines, can_run
from GLPI.Agent.XML import XML


class Libvirt(InventoryModule):
    """Libvirt/KVM/LXC virtual machines detection module using virsh."""

    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled (virsh available)."""
        return can_run('virsh')

    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection using virsh for default and lxc URIs."""
        inventory = params.get('inventory')
        logger = params.get('logger')

        for machine in Libvirt._get_machines(logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

        for machine in Libvirt._get_machines(logger=logger, uri='lxc:///'):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=machine)

    @staticmethod
    def _get_machines(**params) -> List[Dict[str, Any]]:
        uri = params.get('uri')
        logger = params.get('logger')
        uri_param = f"-c {uri}" if uri else ""

        machines = Libvirt._parse_list(
            command=f"virsh {uri_param} --readonly list --all".strip(),
            logger=logger,
        )

        for machine in machines:
            infos = Libvirt._parse_dumpxml(
                command=f"virsh {uri_param} --readonly dumpxml {machine['NAME']}",
                logger=logger,
            )
            if infos:
                machine['MEMORY'] = infos.get('memory')
                machine['UUID'] = infos.get('uuid')
                machine['SUBSYSTEM'] = infos.get('vmtype')
                machine['VCPU'] = infos.get('vcpu')

        return machines

    @staticmethod
    def _parse_list(**params) -> List[Dict[str, Any]]:
        lines = get_all_lines(**params) or []
        machines: List[Dict[str, Any]] = []

        for line in lines:
            if line.strip().startswith('Id'):
                continue
            if line.startswith('-----'):
                continue

            # Expected format: Id Name State (or with blanks for Id)
            # Regex ported from perl: ^\s*(\d+|)(\-|)\s+(\S+)\s+(\S.+)
            import re
            m = re.match(r"^\s*(\d+|)(\-|)\s+(\S+)\s+(\S.+)", line)
            if not m:
                continue

            name = m.group(3)

            # ignore Xen Dom0
            if name == 'Domain-0':
                continue

            status = m.group(4)
            status = status.replace('shut off', 'off', 1) if status.startswith('shut off') else status

            machines.append({
                'NAME': name,
                'STATUS': status,
                'VMTYPE': 'libvirt',
            })

        return machines

    @staticmethod
    def _get_key_text(value):
        if isinstance(value, dict):
            return value.get('#text')
        return value

    @staticmethod
    def _parse_dumpxml(**params) -> Optional[Dict[str, Any]]:
        lines = get_all_lines(**params)
        logger = params.get('logger')
        if not lines:
            if logger:
                logger.error('No virsh xmldump output')
            return None

        try:
            data = XML(string='\n'.join(lines)).dump_as_hash()
        except Exception:
            if logger:
                logger.error('Failed to parse XML output')
            return None

        domain = data.get('domain', {}) if isinstance(data, dict) else {}
        vcpu = Libvirt._get_key_text(domain.get('vcpu'))
        uuid = Libvirt._get_key_text(domain.get('uuid'))
        vmtype = domain.get('-type')
        memory = None
        current_memory = Libvirt._get_key_text(domain.get('currentMemory'))
        if isinstance(current_memory, str):
            import re
            m = re.match(r"(\d+)\d{3}$", current_memory)
            if m:
                memory = int(m.group(1))

        return {
            'vcpu': vcpu,
            'uuid': uuid,
            'vmtype': vmtype,
            'memory': memory,
        }

