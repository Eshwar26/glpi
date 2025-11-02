#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris CPU - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_all_lines, get_sanitized_string
from GLPI.Agent.Tools.Generic import uniq


class CPU(InventoryModule):
    """Solaris CPU detection module."""
    
    category = "cpu"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        for cpu in CPU._get_cpus():
            if inventory:
                inventory.add_entry(
                    section='CPUS',
                    entry=cpu
                )
    
    @staticmethod
    def _get_cpus(**params) -> List[Dict[str, Any]]:
        """Get CPU information."""
        # get virtual CPUs from psrinfo -v
        all_virtual_cpus = CPU._get_virtual_cpus(logger=params.get('logger'))
        
        # get physical CPUs from psrinfo -vp
        all_physical_cpus = CPU._get_physical_cpus(logger=params.get('logger'))
        
        # count the different speed values
        # None is temporarily mapped to 0, to avoid comparison issues
        physical_speeds = sorted(uniq([cpu.get('speed') or 0 for cpu in all_physical_cpus]))
        physical_speeds = [s if s else None for s in physical_speeds]
        
        virtual_speeds = sorted(uniq([cpu.get('speed') or 0 for cpu in all_virtual_cpus]))
        virtual_speeds = [s if s else None for s in virtual_speeds]
        
        cpus = []
        
        # process CPUs by groups, according to their speed
        while physical_speeds:
            physical_speed = physical_speeds.pop(0)
            virtual_speed = virtual_speeds.pop(0) if virtual_speeds else None
            
            physical_cpus = ([cpu for cpu in all_physical_cpus if cpu.get('speed') == physical_speed]
                           if physical_speed else
                           [cpu for cpu in all_physical_cpus if not cpu.get('speed')])
            virtual_cpus = ([cpu for cpu in all_virtual_cpus if cpu.get('speed') == virtual_speed]
                          if virtual_speed else
                          [cpu for cpu in all_virtual_cpus if not cpu.get('speed')])
            
            speed = physical_cpus[0].get('speed') if physical_cpus else (virtual_cpus[0].get('speed') if virtual_cpus else None)
            cpu_type = physical_cpus[0].get('type') if physical_cpus else (virtual_cpus[0].get('type') if virtual_cpus else None)
            
            manufacturer = None
            if cpu_type:
                if 'SPARC' in cpu_type:
                    manufacturer = 'SPARC'
                elif 'Xeon' in cpu_type or 'Intel' in cpu_type:
                    manufacturer = 'Intel'
                elif 'AMD' in cpu_type:
                    manufacturer = 'AMD'
            
            cpus_count = len(physical_cpus)
            
            # Determine cores and threads based on CPU type
            cores, threads = None, None
            if cpu_type == 'UltraSPARC-IV':
                cores, threads = 2, 1
            elif cpu_type == 'UltraSPARC-T1':
                cores, threads = None, 4
            elif cpu_type in ['UltraSPARC-T2', 'UltraSPARC-T2+']:
                cores, threads = None, 8
            elif cpu_type == 'SPARC-T3':
                cores, threads = None, 8
            elif cpu_type == 'SPARC-T4':
                cores, threads = 8, 8
            elif cpu_type == 'SPARC-T5':
                cores, threads = 16, 8
            elif cpu_type in ['SPARC-M7', 'SPARC-M8']:
                cores, threads = 32, 8
            elif cpu_type == 'SPARC64-VI':
                cores, threads = 2, 2
            elif cpu_type in ['SPARC64-VII', 'SPARC64-VII+', 'SPARC64-VII++']:
                cores, threads = 4, 2
            elif cpu_type == 'SPARC64-VIII':
                cores, threads = 8, 2
            else:
                cores, threads = 1, 1
            
            # Get core and threads from physical cpu if set
            if physical_cpus and physical_cpus[0].get('cores') and physical_cpus[0].get('count'):
                cores = physical_cpus[0]['cores']
                threads = int(physical_cpus[0]['count'] / cores)
            
            if cpu_type:
                if 'MB86907' in cpu_type:
                    cpu_type = f"TurboSPARC-II {cpu_type}"
                elif 'MB86904' in cpu_type or '390S10' in cpu_type:
                    cpu_type = ("microSPARC-II " if speed and speed > 70 else "microSPARC ") + cpu_type
                elif ',RT62' in cpu_type and ('5' in cpu_type or '6' in cpu_type):
                    cpu_type = f"hyperSPARC {cpu_type}"
            
            # deduce core numbers from number of virtual cpus if needed
            if not cores:
                # cores may be < 1 in case of virtualization
                cores = len(virtual_cpus) / threads / cpus_count if threads and cpus_count else 1
            
            # Type may contain core number information
            if cpu_type:
                core_match = re.match(r'^(.*) (\d+)-Core', cpu_type)
                if core_match:
                    cpu_type = core_match.group(1)
                    cores = int(core_match.group(2))
            
            for _ in range(cpus_count):
                cpus.append({
                    'MANUFACTURER': manufacturer,
                    'NAME': cpu_type,
                    'SPEED': speed,
                    'CORE': cores,
                    'THREAD': threads
                })
        
        return cpus
    
    @staticmethod
    def _get_virtual_cpus(**params) -> List[Dict[str, Any]]:
        """Get virtual CPUs from psrinfo -v."""
        if 'command' not in params:
            params['command'] = '/usr/sbin/psrinfo -v'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        cpus = []
        for line in lines:
            match = re.match(r'The (\S+) processor operates at (\d+) MHz', line)
            if match:
                cpus.append({
                    'type': match.group(1),
                    'speed': int(match.group(2)),
                })
        
        return cpus
    
    @staticmethod
    def _get_physical_cpus(**params) -> List[Dict[str, Any]]:
        """Get physical CPUs from psrinfo -vp."""
        if 'command' not in params:
            params['command'] = '/usr/sbin/psrinfo -vp'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        cpus = []
        for line in lines:
            line = get_sanitized_string(line)
            
            match = re.match(r'^The physical processor has (\d+) virtual', line)
            if match:
                cpus.append({'count': int(match.group(1))})
                continue
            
            match = re.match(r'^The physical processor has (\d+) cores and (\d+) virtual', line)
            if match:
                cpus.append({
                    'cores': int(match.group(1)),
                    'count': int(match.group(2))
                })
                continue
            
            match = re.match(r'^The (\S+) physical processor has (\d+) virtual', line)
            if match:
                cpus.append({
                    'type': match.group(1),
                    'count': int(match.group(2))
                })
                continue
            
            match = re.match(r'(\S+) \(.* clock (\d+) MHz\)', line)
            if match and cpus:
                cpu = cpus[-1]
                cpu['type'] = match.group(1)
                cpu['speed'] = int(match.group(2))
                continue
            
            if cpus:
                cpu = cpus[-1]
                xeon_match = re.search(r'Intel\(r\) Xeon\(r\) CPU +(\S+)', line)
                if xeon_match:
                    cpu['type'] = f"Xeon {xeon_match.group(1)}"
                else:
                    core_match = re.search(r'Intel\(r\) Core\(tm\) (\S+) CPU', line)
                    if core_match:
                        cpu['type'] = f"Intel Core {core_match.group(1)}"
                    else:
                        proc_match = re.search(r'(\S.+) Processor', line)
                        if proc_match:
                            cpu['type'] = proc_match.group(1)
        
        return cpus
