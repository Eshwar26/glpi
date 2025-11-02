#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD MIPS - Python Implementation
"""

import re
import platform
from typing import Any, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_first_line, get_all_lines


class MIPS(InventoryModule):
    """BSD MIPS inventory module."""
    
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
            return bool(uname_m and re.match(r'^mips', uname_m))
        
        # Check architecture
        arch = platform.machine()
        return bool(re.match(r'^mips', arch))
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        no_category = params.get('no_category', {})
        
        bios = {
            'SMANUFACTURER': 'SGI',
        }
        
        # sysctl infos
        # example on NetBSD: SGI-IP22
        # example on OpenBSD: SGI-O2 (IP32)
        smodel = get_first_line(command='sysctl -n hw.model')
        if smodel:
            bios['SMODEL'] = smodel
        
        count_str = get_first_line(command='sysctl -n hw.ncpu')
        count = int(count_str) if count_str and count_str.isdigit() else 0
        
        # dmesg infos
        # I) Indy
        # NetBSD:
        # mainbus0 (root): SGI-IP22 [SGI, 6906e152], 1 processor
        # cpu0 at mainbus0: MIPS R4400 CPU (0x450) Rev. 5.0 with MIPS R4010 FPC Rev. 0.0
        # int0 at mainbus0 addr 0x1fbd9880: bus 75MHz, CPU 150MHz
        #
        # II) O2
        # NetBSD:
        # mainbus0 (root): SGI-IP32 [SGI, 8], 1 processor
        # cpu0 at mainbus0: MIPS R5000 CPU (0x2321) Rev. 2.1 with built-in FPU Rev. 1.0
        # OpenBSD:
        # mainbus0 (root)
        # cpu0 at mainbus0: MIPS R5000 CPU rev 2.1 180 MHz with R5000 based FPC rev 1.0
        # cpu0: cache L1-I 32KB D 32KB 2 way, L2 512KB direct
        
        cpu: Dict[str, Any] = {}
        dmesg_lines = get_all_lines(command='dmesg')
        if dmesg_lines:
            smodel_pattern = bios.get('SMODEL', '')
            for line in dmesg_lines:
                if smodel_pattern:
                    match = re.search(rf'{re.escape(smodel_pattern)}\s*\[\S*\s*(\S*)\]', line)
                    if match:
                        bios['SSN'] = match.group(1)
                
                match = re.match(r'cpu0 at mainbus0:\s*(.*)$', line)
                if match:
                    cpu['NAME'] = match.group(1)
                
                match = re.search(r'CPU\s*.*\D(\d+)\s*MHz', line)
                if match:
                    cpu['SPEED'] = match.group(1)
        
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
