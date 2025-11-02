#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX CPU - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match, get_first_line, get_lines_count, Uname
from GLPI.Agent.Tools.HPUX import get_info_from_machinfo, is_hpvm_guest


class CPU(InventoryModule):
    """HP-UX CPU detection module."""
    
    category = "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # http://forge.fusioninventory.org/issues/755
        if can_run('/opt/propplus/bin/cprop') and not is_hpvm_guest():
            for cpu in CPU._parse_cprop(
                command='/opt/propplus/bin/cprop -summary -c Processors',
                logger=logger
            ):
                if inventory:
                    inventory.add_entry(section='CPUS', entry=cpu)
            return
        
        cpu_info = None
        if can_run('/usr/contrib/bin/machinfo'):
            cpu_info = CPU._parse_machin_info(
                command='/usr/contrib/bin/machinfo',
                logger=logger
            )
        else:
            # Old HP-UX without machinfo
            cpu_infos = {
                "D200": {"TYPE": "7100LC", "SPEED": 75},
                "D210": {"TYPE": "7100LC", "SPEED": 100},
                "D220": {"TYPE": "7300LC", "SPEED": 132},
                "D230": {"TYPE": "7300LC", "SPEED": 160},
                "D250": {"TYPE": "7200", "SPEED": 100},
                "D260": {"TYPE": "7200", "SPEED": 120},
                "D270": {"TYPE": "8000", "SPEED": 160},
                "D280": {"TYPE": "8000", "SPEED": 180},
                "D310": {"TYPE": "7100LC", "SPEED": 100},
                "D320": {"TYPE": "7300LC", "SPEED": 132},
                "D330": {"TYPE": "7300LC", "SPEED": 160},
                "D350": {"TYPE": "7200", "SPEED": 100},
                "D360": {"TYPE": "7200", "SPEED": 120},
                "D370": {"TYPE": "8000", "SPEED": 160},
                "D380": {"TYPE": "8000", "SPEED": 180},
                "D390": {"TYPE": "8200", "SPEED": 240},
                "K360": {"TYPE": "8000", "SPEED": 180},
                "K370": {"TYPE": "8200", "SPEED": 200},
                "K380": {"TYPE": "8200", "SPEED": 240},
                "K400": {"TYPE": "7200", "SPEED": 140},
                "K410": {"TYPE": "7200", "SPEED": 120},
                "K420": {"TYPE": "7200", "SPEED": 120},
                "K460": {"TYPE": "8000", "SPEED": 180},
                "K570": {"TYPE": "8200", "SPEED": 200},
                "K580": {"TYPE": "8200", "SPEED": 240},
                "L1000-36": {"TYPE": "8500", "SPEED": 360},
                "L1500-7x": {"TYPE": "8700", "SPEED": 750},
                "L3000-7x": {"TYPE": "8700", "SPEED": 750},
                "N4000-44": {"TYPE": "8500", "SPEED": 440},
                "ia64 hp server rx1620": {"TYPE": "itanium", "SPEED": 1600}
            }
            
            device = get_first_line(command='model |cut -f 3- -d/')
            if device and device in cpu_infos:
                cpu_info = cpu_infos[device]
            else:
                cpu_info = {}
                cpu_type = get_first_match(
                    command="echo 'sc product cpu;il' | /usr/sbin/cstm",
                    logger=logger,
                    pattern=r'(\S+)\s+CPU\s+Module'
                )
                if cpu_type:
                    cpu_info['TYPE'] = cpu_type
                
                speed = get_first_match(
                    command="echo 'itick_per_usec/D' | adb -k /stand/vmunix /dev/kmem",
                    logger=logger,
                    pattern=r'tick_per_usec:\s+(\d+)'
                )
                if speed:
                    try:
                        cpu_info['SPEED'] = int(speed)
                    except (ValueError, TypeError):
                        pass
            
            # NBR CPU
            cpu_count = get_lines_count(command='ioscan -Fk -C processor')
            if cpu_count:
                cpu_info['CPUcount'] = cpu_count
        
        serie = Uname('-m')
        if cpu_info.get('TYPE') == 'unknow' and 'ia64' in serie:
            cpu_info['TYPE'] = 'Itanium'
        if '9000' in serie:
            cpu_type = cpu_info.get('TYPE', '')
            cpu_info['TYPE'] = f"PA{cpu_type}"
        
        cpu_count = cpu_info.get('CPUcount', 1)
        for _ in range(cpu_count):
            if inventory:
                inventory.add_entry(section='CPUS', entry=cpu_info)
    
    @staticmethod
    def _parse_machin_info(**params) -> Optional[Dict[str, Any]]:
        """Parse machinfo output."""
        info = get_info_from_machinfo(**params)
        if not info:
            return None
        
        result = {}
        cpu_info = info.get('CPU info')
        
        if isinstance(cpu_info, dict):
            # HPUX 11.23
            result['CPUcount'] = cpu_info.get('number of cpus')
            
            clock_speed = cpu_info.get('clock speed', '')
            match = re.search(r'(\d+) MHz', clock_speed)
            if match:
                result['SPEED'] = int(match.group(1))
            
            processor_model = cpu_info.get('processor model', '')
            if 'Intel' in processor_model:
                result['MANUFACTURER'] = 'Intel'
            if 'Itanium' in processor_model:
                result['NAME'] = 'Itanium'
        else:
            # HPUX 11.31
            if cpu_info:
                match = re.match(r'^(\d+) ', cpu_info)
                if match:
                    result['CPUcount'] = int(match.group(1))
                
                ghz_match = re.search(r'([\d.]+) GHz', cpu_info)
                if ghz_match:
                    result['SPEED'] = int(float(ghz_match.group(1)) * 1000)
                
                if 'Intel' in cpu_info:
                    result['MANUFACTURER'] = 'Intel'
                if 'Itanium' in cpu_info:
                    result['NAME'] = 'Itanium'
                
                logical_match = re.search(r'(\d+) logical processors', cpu_info)
                if logical_match and result.get('CPUcount'):
                    result['CORE'] = int(logical_match.group(1)) / result['CPUcount']
        
        return result
    
    @staticmethod
    def _parse_cprop(**params) -> List[Dict[str, Any]]:
        """Parse cprop output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        cpus = []
        instance = {}
        
        for line in lines:
            if re.match(r'^\[Instance\]: \d+', line):
                # new block
                instance = {}
                continue
            
            match = re.match(r'^ \s+ \[ ([^\]]+) \]: \s (.+)', line, re.VERBOSE)
            if match:
                instance[match.group(1)] = match.group(2)
                continue
            
            if re.match(r'^\*+', line):
                if not instance:
                    continue
                
                processor_type = instance.get('Processor Type', '')
                name = 'Itanium' if 'Itanium' in processor_type else None
                manufacturer = 'Intel' if 'Intel' in processor_type else None
                
                cpu = {
                    'SPEED': instance.get('Processor Speed'),
                    'ID': instance.get('Tag'),
                    'NAME': name,
                    'MANUFACTURER': manufacturer
                }
                
                location = instance.get('Location', '')
                slot_match = re.search(r'Cell Slot Number (\d+)\b', location, re.IGNORECASE)
                if slot_match:
                    # this is a single core from a multi-core cpu
                    slot_id = int(slot_match.group(1))
                    # Extend list if needed
                    while len(cpus) <= slot_id:
                        cpus.append(None)
                    
                    if cpus[slot_id]:
                        cpus[slot_id]['CORE'] = cpus[slot_id].get('CORE', 0) + 1
                    else:
                        cpus[slot_id] = cpu
                        cpus[slot_id]['CORE'] = 1
                else:
                    cpus.append(cpu)
        
        # filter missing cpus
        cpus = [cpu for cpu in cpus if cpu]
        
        return cpus
