#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD SPARC - Python Implementation
"""

import re
import platform
from typing import Any, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_line, get_all_lines, dec2hex


class SPARC(InventoryModule):
    """BSD SPARC inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "bios"
    
    @staticmethod
    def other_categories():
        """Return other categories this module handles."""
        return ['cpu']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        remote = params.get('remote')
        if remote:
            uname_m = uname("-m")
            return bool(uname_m and re.match(r'^sparc', uname_m))
        
        # Check architecture
        arch = platform.machine()
        return bool(re.match(r'^sparc', arch))
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        no_category = params.get('no_category', {})
        
        bios = {
            'SMANUFACTURER': 'SUN',
        }
        
        # sysctl infos
        # it gives only the CPU on OpenBSD/sparc64
        smodel = get_first_line(command='sysctl -n hw.model')
        if smodel:
            bios['SMODEL'] = smodel
        
        # example on NetBSD: 0x807b65c
        # example on OpenBSD: 2155570635
        ssn = get_first_line(command='sysctl -n kern.hostid')
        if ssn:
            # force hexadecimal, but remove 0x to make it appear as in the firmware
            ssn_hex = dec2hex(ssn)
            if ssn_hex:
                bios['SSN'] = ssn_hex.replace('0x', '')
        
        count_str = get_first_line(command='sysctl -n hw.ncpu')
        count = int(count_str) if count_str and count_str.isdigit() else 0
        
        # dmesg infos
        # I) SPARC
        # NetBSD:
        # mainbus0 (root): SUNW,SPARCstation-20: hostid 72362bb1
        # cpu0 at mainbus0: TMS390Z50 v0 or TMS390Z55 @ 50 MHz, on-chip FPU
        # OpenBSD:
        # mainbus0 (root): SUNW,SPARCstation-20
        # cpu0 at mainbus0: TMS390Z50 v0 or TMS390Z55 @ 50 MHz, on-chip FPU
        #
        # II) SPARC64
        # NetBSD:
        # mainbus0 (root): SUNW,Ultra-1: hostid 807b65cb
        # cpu0 at mainbus0: SUNW,UltraSPARC @ 166.999 MHz, version 0 FPU
        # OpenBSD:
        # mainbus0 (root): Sun Ultra 1 SBus (UltraSPARC 167MHz)
        # cpu0 at mainbus0: SUNW,UltraSPARC @ 166.999 MHz, version 0 FPU
        # FreeBSD:
        # cpu0: Sun Microsystems UltraSparc-I Processor (167.00 MHz CPU)
        
        cpu: Dict[str, Any] = {}
        dmesg_lines = get_all_lines(command='dmesg')
        if dmesg_lines:
            for line in dmesg_lines:
                match = re.match(r'^mainbus0 \(root\):\s*(.*)$', line)
                if match:
                    bios['SMODEL'] = match.group(1)
                
                match = re.match(r'^cpu[^:]*:\s*(.*)$', line, re.IGNORECASE)
                if match:
                    cpu['NAME'] = match.group(1)
        
        # Clean up SMODEL
        if 'SMODEL' in bios and bios['SMODEL']:
            bios['SMODEL'] = re.sub(r'SUNW,', '', bios['SMODEL'])
            bios['SMODEL'] = re.sub(r'[:\(].*$', '', bios['SMODEL'])
            bios['SMODEL'] = bios['SMODEL'].strip()
        
        # Clean up CPU name
        if 'NAME' in cpu and cpu['NAME']:
            cpu['NAME'] = re.sub(r'SUNW,', '', cpu['NAME'])
            cpu['NAME'] = cpu['NAME'].strip()
        
        # XXX quick and dirty _attempt_ to get proc speed
        if 'NAME' in cpu and cpu['NAME']:
            match = re.search(r'(\d+)(\.\d+|)\s*mhz', cpu['NAME'], re.IGNORECASE)
            if match:
                # possible decimal point, round number
                speed_str = f"{match.group(1)}{match.group(2)}"
                try:
                    cpu['SPEED'] = int(round(float(speed_str)))
                except ValueError:
                    pass
        
        if inventory:
            inventory.set_bios(bios)
        
        if no_category.get('cpu'):
            return
        
        # Add CPU entries
        for _ in range(count):
            if inventory:
                inventory.add_entry(
                    section='CPUS',
                    entry=cpu
                )
