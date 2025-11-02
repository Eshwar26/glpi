#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX CPU - Python Implementation
"""

import re
from typing import Dict, Any, List

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import uname, get_all_lines, get_first_line


class CPU(InventoryModule):
    """AIX CPU inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        cpus = CPU._get_cpus(
            command='lsdev -Cc processor -F name',
            logger=logger
        )
        
        for cpu in cpus:
            if inventory:
                inventory.add_entry(
                    section='CPUS',
                    entry=cpu
                )
    
    @staticmethod
    def _get_cpus(**params) -> List[Dict[str, Any]]:
        """Get CPU information."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        aix_version_str = uname("-v")
        aix_version = int(aix_version_str) if aix_version_str and aix_version_str.isdigit() else 0
        
        cpus = []
        for line in lines:
            device = line.strip()
            
            format_str = 'type:frequency:frequency' if aix_version >= 5 else 'type'
            
            lsattr_lines = get_all_lines(
                command=f"lsattr -EOl {device} -a '{format_str}'"
            )
            
            cpu = {
                'THREAD': 1
            }
            
            smt_threads = get_first_line(
                command=f"lsattr -EOl {device} -a 'state:type:smt_threads'"
            )
            if smt_threads:
                match = re.search(r':(\d+)$', smt_threads)
                if match:
                    cpu['THREAD'] = int(match.group(1))
            
            # drop headers
            if lsattr_lines:
                lsattr_lines = lsattr_lines[1:]
            
            if not lsattr_lines:
                continue
            
            # use first line to compute name, frequency and number of threads
            infos = lsattr_lines[0].split(':')
            
            cpu['NAME'] = infos[0].replace('_', ' ')
            
            if aix_version >= 5 and len(infos) > 1:
                try:
                    freq = int(infos[1])
                    # Round up if remainder >= 50000
                    if (freq % 1000000) >= 50000:
                        cpu['SPEED'] = int(freq / 1000000) + 1
                    else:
                        cpu['SPEED'] = int(freq / 1000000)
                except (ValueError, IndexError):
                    pass
            else:
                # On older models, frequency is based on cpu model and uname
                cpu_type = infos[0] if infos else ''
                
                if cpu_type in ('PowerPC', 'PowerPC_601', 'PowerPC_604'):
                    uname_m = uname("-m")
                    if uname_m:
                        if re.search(r'E1D|EAD|C1D|R04|C4D|R4D', uname_m):
                            cpu['SPEED'] = 12.2
                        elif re.search(r'34M', uname_m):
                            cpu['SPEED'] = 133
                        elif re.search(r'N4D', uname_m):
                            cpu['SPEED'] = 150
                        elif re.search(r'X4M|X4D', uname_m):
                            cpu['SPEED'] = 200
                        elif re.search(r'N4E|K04|K44', uname_m):
                            cpu['SPEED'] = 225
                        elif re.search(r'N4F', uname_m):
                            cpu['SPEED'] = 320
                        elif re.search(r'K45', uname_m):
                            cpu['SPEED'] = 360
                        else:
                            cpu['SPEED'] = 225
                elif cpu_type == 'PowerPC_RS64_III':
                    cpu['SPEED'] = 400
                elif cpu_type == 'PowerPC_620':
                    cpu['SPEED'] = 172
                else:
                    cpu['SPEED'] = 225
            
            # compute core number from lines number
            cpu['CORE'] = len(lsattr_lines)
            
            cpus.append(cpu)
        
        return cpus
