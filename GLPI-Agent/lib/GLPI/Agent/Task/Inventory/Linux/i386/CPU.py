#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux i386 CPU - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_canonical_manufacturer
from GLPI.Agent.Tools.Linux import get_cpus_from_proc
from GLPI.Agent.Tools.Generic import get_cpus_from_dmidecode


class CPU(InventoryModule):
    """i386/x86_64 CPU detection module."""
    
    category = "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/cpuinfo')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for cpu in CPU._get_cpus(logger=logger):
            if inventory:
                inventory.add_entry(section='CPUS', entry=cpu)
    
    @staticmethod
    def _get_cpus(**params) -> List[Dict[str, Any]]:
        """Get CPU information combining /proc/cpuinfo and dmidecode."""
        dmidecode_file = params.get('dmidecode')
        dmidecode_infos = (
            get_cpus_from_dmidecode(file=dmidecode_file) if dmidecode_file
            else get_cpus_from_dmidecode()
        )
        
        count = 0
        cpus = []
        seen = {}
        
        for logical_cpu in get_cpus_from_proc(**params):
            cpu_id = logical_cpu.get('physical id')
            core = None
            thread = None
            
            if cpu_id is not None:
                if cpu_id in seen:
                    continue
                seen[cpu_id] = True
                
                core = logical_cpu.get('cpu cores')
                siblings = logical_cpu.get('siblings')
                if core and siblings and int(siblings) >= int(core):
                    thread = int(siblings) / int(core)
                else:
                    thread = 1
                
                # Support case thread count is not an integer
                # This can happen if cpu provides performance and efficiency cores
                if thread > int(thread):
                    thread = int(thread) + 1
            else:
                cpu_id = count
                core = 1
                thread = 1
            
            dmidecode_info = dmidecode_infos[cpu_id] if cpu_id < len(dmidecode_infos) else {}
            
            cpu = {
                'ARCH': 'i386',
                'MANUFACTURER': get_canonical_manufacturer(logical_cpu.get('vendor_id', '')),
                'STEPPING': logical_cpu.get('stepping') or dmidecode_info.get('STEPPING'),
                'FAMILYNUMBER': logical_cpu.get('cpu family') or dmidecode_info.get('FAMILYNUMBER'),
                'MODEL': logical_cpu.get('model') or dmidecode_info.get('MODEL'),
                'NAME': logical_cpu.get('model name'),
                'CORE': core or dmidecode_info.get('CORE'),
                'THREAD': thread or dmidecode_info.get('THREAD')
            }
            
            # Import some dmidecode value only when available
            for key in ['ID', 'SERIAL', 'EXTERNAL_CLOCK', 'FAMILYNAME', 'CORECOUNT']:
                if dmidecode_info.get(key):
                    cpu[key] = dmidecode_info[key]
            
            # Extract speed from NAME
            if cpu.get('NAME'):
                speed_match = re.search(r'([\d\.]+)\s*(GHZ|MHZ)', cpu['NAME'], re.IGNORECASE)
                if speed_match:
                    speed_val = float(speed_match.group(1))
                    unit = speed_match.group(2).lower()
                    multiplier = 1000 if unit == 'ghz' else 1
                    cpu['SPEED'] = int(speed_val * multiplier)
            
            cpus.append(cpu)
            count += 1
        
        return cpus
