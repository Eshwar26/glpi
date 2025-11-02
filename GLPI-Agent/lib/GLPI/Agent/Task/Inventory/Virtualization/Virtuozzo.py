#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Virtuozzo - Python Implementation
"""

from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match
from GLPI.Agent.Tools.Network import mac_address_pattern
from GLPI.Agent.Tools.Virtualization import STATUS_RUNNING, STATUS_PAUSED, STATUS_OFF


class Virtuozzo(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        # Avoid duplicated entry with libvirt
        if can_run('virsh'):
            return False
        return can_run('vzlist')

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        for vz in Virtuozzo._parse_vzlist(inventory=inventory, logger=logger):
            if inventory:
                inventory.add_entry(section='VIRTUALMACHINES', entry=vz)

    @staticmethod
    def _parse_vzlist(**params) -> List[Dict[str, Any]]:
        inventory = params.get('inventory')
        logger = params.get('logger')

        lines = get_all_lines(
            command='vzlist --all --no-header -o hostname,ctid,cpulimit,status,ostemplate',
            logger=logger,
        ) or []
        if not lines:
            return []

        confctid_template = params.get('ctid_template') or '/etc/vz/conf/__XXX__.conf'

        host_id = ''
        try:
            host_id = inventory.getHardware('UUID') if inventory else ''
        except Exception:
            host_id = ''

        status_list = {
            'stopped': STATUS_OFF,
            'running': STATUS_RUNNING,
            'paused': STATUS_PAUSED,
            'mounted': STATUS_OFF,
            'suspended': STATUS_PAUSED,
            'unknown': STATUS_OFF,
        }

        result: List[Dict[str, Any]] = []
        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            name, ctid, cpus, status, subsys = parts[0], parts[1], parts[2], parts[3], parts[4]

            ctid_conf = confctid_template.replace('__XXX__', ctid)

            memory = get_first_match(file=ctid_conf, pattern=r'^SLMMEMORYLIMIT="\d+:(\d+)"$', logger=logger)
            if memory:
                try:
                    memory = int(memory) / 1024 / 1024
                except Exception:
                    memory = None
            else:
                memory = get_first_match(file=ctid_conf, pattern=r'^PRIVVMPAGES="\d+:(\d+)"$', logger=logger)
                if memory:
                    try:
                        memory = int(memory) * 4 / 1024
                    except Exception:
                        memory = None
                else:
                    memory = get_first_match(file=ctid_conf, pattern=r'^PHYSPAGES="\d+:(\d+\w{0,1})"$', logger=logger)
                    if memory:
                        import re
                        m = re.match(r'^(\d+)(\w{0,1})$', str(memory))
                        if m:
                            num = int(m.group(1))
                            unit = m.group(2)
                            if unit == 'M':
                                memory = num
                            elif unit == 'G':
                                memory = num * 1024
                            elif unit == 'K':
                                memory = num / 1024
                            else:
                                memory = num / 1024 / 1024

            uuid = f"{host_id}-{ctid}" if host_id else ctid
            status_norm = status_list.get(status, STATUS_OFF)

            container: Dict[str, Any] = {
                'NAME': name,
                'VCPU': cpus,
                'UUID': uuid,
                'MEMORY': memory,
                'STATUS': status_norm,
                'SUBSYSTEM': subsys,
                'VMTYPE': 'virtuozzo',
            }

            mac = Virtuozzo._get_macs(status=status_norm, ctid=ctid, logger=logger)
            if mac:
                container['MAC'] = mac

            result.append(container)

        return result

    @staticmethod
    def _get_macs(**params) -> Optional[str]:
        status = params.get('status')
        ctid = params.get('ctid')
        logger = params.get('logger')

        if not status or status != STATUS_RUNNING:
            return None

        lines = get_all_lines(command=f"vzctl exec '{ctid}' 'ip -0 a'", logger=logger) or []
        macs: List[str] = []
        import re
        for line in lines:
            m = re.match(rf'^\s+link/ether ({mac_address_pattern})\s', line, re.IGNORECASE)
            if m:
                macs.append(m.group(1))
        return '/'.join(macs) if macs else None

