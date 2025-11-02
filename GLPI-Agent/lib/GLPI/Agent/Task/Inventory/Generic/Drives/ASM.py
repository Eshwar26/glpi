#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Drives ASM - Python Implementation
"""

import os
import re
import platform
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import trim_whitespace, can_read
from GLPI.Agent.Tools.Unix import get_processes, get_first_line, get_all_lines


class ASM(InventoryModule):
    """Oracle ASM drives inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        if platform.system() == 'Windows':
            return False
        processes = get_processes(filter_re=r'^asm_pmon', namespace="same")
        return bool(processes)
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # First get asm_pmon process
        processes = get_processes(filter_re=r'^asm_pmon', namespace="same", logger=logger)
        if not processes:
            return
        
        asm_pmon = processes[0]
        user = asm_pmon.get('USER')
        
        match = re.search(r'(\+ASM.*)$', asm_pmon.get('CMD', ''))
        if not match:
            return
        asm = match.group(1)
        
        # Then lookup GRID_HOME in user's environment
        root = (user == 'root')
        grid_home = None
        if root:
            grid_home = os.environ.get('GRID_HOME')
        else:
            grid_home = get_first_line(command=f"su - {user} -c 'echo $GRID_HOME'")
        
        if not grid_home and can_read("/etc/oratab"):
            oratab = get_all_lines(file="/etc/oratab")
            asm_for_re = re.escape(asm)
            matching_lines = [line for line in oratab if re.match(f'^{asm_for_re}:', line)]
            if matching_lines:
                line = matching_lines[0]
                match = re.match(f'^{asm_for_re}:([^:]+):', line)
                if match:
                    grid_home = match.group(1)
        
        # Oracle documentation:
        # see https://docs.oracle.com/cd/E11882_01/server.112/e18951/asm_util004.htm#OSTMG94549
        # But also try oracle user if grid user doesn't exist, and finally try as root
        cmd = (f"{grid_home}/bin/" if grid_home else "") + "asmcmd lsdg"
        
        if root:
            old_oracle_sid = os.environ.get('ORACLE_SID')
            old_oracle_home = os.environ.get('ORACLE_HOME')
            os.environ['ORACLE_SID'] = asm
            if grid_home:
                os.environ['ORACLE_HOME'] = grid_home
        else:
            cmd = f'su - {user} -c "ORACLE_SID={asm} ORACLE_HOME={grid_home} {cmd}"'
        
        diskgroups = ASM._get_disks_groups(command=cmd, logger=logger)
        
        # Restore environment if we modified it
        if root:
            if old_oracle_sid:
                os.environ['ORACLE_SID'] = old_oracle_sid
            elif 'ORACLE_SID' in os.environ:
                del os.environ['ORACLE_SID']
            if old_oracle_home:
                os.environ['ORACLE_HOME'] = old_oracle_home
            elif 'ORACLE_HOME' in os.environ:
                del os.environ['ORACLE_HOME']
        
        if not diskgroups:
            return
        
        # Add disks groups inventory as DRIVES
        for diskgroup in diskgroups:
            name = diskgroup.get('NAME')
            if not name:
                continue
            
            # Only report mounted group
            if not (diskgroup.get('STATE') and diskgroup['STATE'] == 'MOUNTED'):
                continue
            
            if inventory:
                inventory.add_entry(
                    section='DRIVES',
                    entry={
                        'LABEL': name,
                        'VOLUMN': 'diskgroup',
                        'TOTAL': diskgroup.get('TOTAL'),
                        'FREE': diskgroup.get('FREE')
                    }
                )
    
    @staticmethod
    def _get_disks_groups(**params) -> Optional[List[Dict[str, Any]]]:
        """Get ASM disk groups."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        groups = []
        line_count = 0
        for line in lines:
            # Cleanup line
            line = trim_whitespace(line)
            
            # Logic to skip header
            line_count += 1
            if line_count == 1 and re.match(r'^State.*Name$', line):
                continue
            
            infos = line.split()
            if len(infos) not in [13, 14]:
                continue
            
            # Cleanup trailing slash on NAME
            infos[-1] = re.sub(r'/+$', '', infos[-1])
            
            # Fix total against TYPE field
            total = int(infos[-7] or 0) - int(infos[-5] or 0)
            if re.match(r'^NORMAL|HIGH$', infos[1]):
                total /= 3 if infos[1] == 'HIGH' else 2
            
            groups.append({
                'NAME': infos[-1] or 'NONAME',
                'STATE': infos[0] or 'UNKNOWN',
                'TYPE': infos[1] or 'EXTERN',
                'TOTAL': int(total),
                'FREE': int(infos[-4])
            })
        
        return groups
