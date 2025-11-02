#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Virtualization Solaris Zones - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import (
    can_run,
    get_all_lines,
    get_first_line,
    get_first_match,
    empty,
)
from GLPI.Agent.XML import XML


class SolarisZones(InventoryModule):
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        # Requires Solaris-specific helpers; we approximate getZone by /sbin/zonename
        if not can_run('zoneadm'):
            return False
        zonename = get_first_line(command='/usr/bin/zonename')
        if zonename != 'global':
            return False
        return SolarisZones._check_solaris_valid_release()

    @staticmethod
    def doInventory(**params: Any) -> None:
        inventory = params.get('inventory')
        logger = params.get('logger')

        zones = get_all_lines(command='/usr/sbin/zoneadm list -ip', logger=logger) or []
        for zone in zones:
            parts = zone.split(':')
            if len(parts) < 6:
                continue
            zoneid, zonename, zonestatus, _, uuid, zonebrand = parts[:6]
            if zonename == 'global':
                continue

            zonestatus = 'off' if zonestatus == 'installed' else zonestatus
            zonebrand = 'Solaris Zones' if (not zonebrand or empty(zonebrand)) else zonebrand

            zonefile = f'/etc/zones/{zonename}.xml'

            memory = None
            vcpu = get_first_match(
                command='/usr/sbin/psrinfo -p -v',
                pattern=r'The physical processor has \d+ cores and (\d+) virtual processors',
                logger=logger,
            )

            zone_xml_lines = get_all_lines(file=zonefile)
            config = None
            if zone_xml_lines:
                config = XML(string='\n'.join(zone_xml_lines), force_array=['rctl']).dump_as_hash()

            if config and isinstance(config.get('zone', {}).get('rctl'), list):
                for name in ['zone.max-locked-memory', 'zone.max-physical-memory']:
                    conf = next((r for r in config['zone']['rctl'] if r.get('-name') == name), None)
                    if conf and conf.get('rctl-value') and conf['rctl-value'].get('-limit'):
                        limit = conf['rctl-value']['-limit']
                        from GLPI.Agent.Tools import get_canonical_size as _gcs
                        memory = _gcs(f'{limit}bytes', 1024)
                    if memory:
                        break
                cpucap = next((r for r in config['zone']['rctl'] if r.get('-name') == 'zone.cpu-cap'), None)
                if cpucap and cpucap.get('rctl-value') and cpucap['rctl-value'].get('-limit'):
                    try:
                        vcpu = int(int(cpucap['rctl-value']['-limit']) / 100)
                    except Exception:
                        pass
            else:
                line = get_first_match(file=zonefile, pattern=r'(.*mcap.*)', logger=logger)
                if line:
                    memcap = re.sub(r'[^\d]+', '', line)
                    try:
                        memory = int(memcap) / 1024 / 1024
                    except Exception:
                        memory = None
                if not vcpu:
                    vcpu = get_first_line(command='/usr/sbin/psrinfo -p', logger=logger)

            if inventory:
                inventory.add_entry(
                    section='VIRTUALMACHINES',
                    entry={
                        'MEMORY': memory,
                        'NAME': zonename,
                        'UUID': uuid,
                        'STATUS': zonestatus,
                        'SUBSYSTEM': zonebrand,
                        'VMTYPE': 'Solaris Zones',
                        'VCPU': vcpu,
                    },
                )

    @staticmethod
    def _check_solaris_valid_release() -> bool:
        # Approximate: parse /etc/release for 10 8/07+ or >10
        rel = get_all_lines(file='/etc/release') or []
        text = '\n'.join(rel)
        m = re.search(r'Solaris\s+(\d+)', text)
        if not m:
            return False
        version = int(m.group(1))
        if version > 10:
            return True
        if version == 10:
            # Look for subversion like s10_?? or 8/07 or later
            if re.search(r'(?:08/07|\b10\b|11/06|\b2007\b|\b2008\b|\b2009\b|\b2010\b)', text):
                return True
        return False

