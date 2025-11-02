#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Memory - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match, Uname, get_canonical_size
from GLPI.Agent.Tools.HPUX import is_hpvm_guest


class Memory(InventoryModule):
    """HP-UX memory detection module."""
    
    category = "memory"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        memories = []
        
        # http://forge.fusioninventory.org/issues/754
        if can_run('/opt/propplus/bin/cprop') and not is_hpvm_guest():
            memories = Memory._parse_cprop(
                command='/opt/propplus/bin/cprop -summary -c Memory',
                logger=logger
            )
        else:
            arch = Uname('-m')
            
            if 'ia64' in arch:
                # enable infolog
                import subprocess
                try:
                    subprocess.run("echo 'sc product  IPF_MEMORY;info' | /usr/sbin/cstm", 
                                 shell=True, capture_output=True)
                except Exception:
                    pass
                
                memories = Memory._parse_cstm64(
                    command="echo 'sc product IPF_MEMORY;il' | /usr/sbin/cstm",
                    logger=logger
                )
            else:
                memories = Memory._parse_cstm(
                    command="echo 'sc product mem;il'| /usr/sbin/cstm",
                    logger=logger
                )
        
        memory_size = 0
        swap_size_str = get_first_match(
            command='swapinfo -dt',
            logger=logger,
            pattern=r'^total\s+(\d+)'
        )
        
        for memory in memories:
            if inventory:
                inventory.add_entry(
                    section='MEMORIES',
                    entry=memory
                )
            capacity = memory.get('CAPACITY')
            if capacity:
                try:
                    memory_size += int(capacity)
                except (ValueError, TypeError):
                    pass
        
        swap_size = None
        if swap_size_str:
            try:
                swap_size = int(int(swap_size_str) / 1024)
            except (ValueError, TypeError):
                pass
        
        if inventory:
            inventory.set_hardware({
                'SWAP': swap_size,
                'MEMORY': memory_size
            })
    
    @staticmethod
    def _parse_cprop(**params) -> List[Dict[str, Any]]:
        """Parse cprop output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        memories = []
        instance = {}
        
        for line in lines:
            if re.match(r'\[Instance\]: \d+', line):
                # new block
                instance = {}
                continue
            
            match = re.match(r'^ \s+ \[ ([^\]]+) \]: \s (\S+.*)', line, re.VERBOSE)
            if match:
                instance[match.group(1)] = match.group(2)
                continue
            
            if re.match(r'^\*+', line):
                if not instance or not instance.get('Size'):
                    continue
                memories.append({
                    'CAPACITY': get_canonical_size(instance['Size'], 1024),
                    'DESCRIPTION': instance.get('Part Number'),
                    'SERIALNUMBER': instance.get('Serial Number'),
                    'TYPE': instance.get('Module Type'),
                })
        
        return memories
    
    @staticmethod
    def _parse_cstm(**params) -> List[Dict[str, Any]]:
        """Parse cstm output for PA-RISC systems."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        memories = []
        
        capacities = {}
        capacity = 0
        description = None
        numslot = 1
        subnumslot = None
        serialnumber = 'No Serial Number available!'
        mem_type = None
        ok = False
        
        for line in lines:
            if re.search(r'FRU\sSource\s+=\s+\S+\s+\(memory', line):
                ok = False
            
            if re.search(r'Source\s+Detail\s+=\s4', line):
                ok = True
            
            cap_match = re.match(r'\s+(\d+)\s+(\d+)', line)
            if cap_match:
                capacities[int(cap_match.group(1))] = int(cap_match.group(2))
            
            ext_match = re.search(r'Extender\s+Location\s+=\s+(\S+)', line)
            if ext_match:
                subnumslot = ext_match.group(1)
            
            rank_match = re.search(r'DIMMS\s+Rank\s+=\s+(\S+)', line)
            if rank_match:
                try:
                    numslot = f"{int(rank_match.group(1)):02x}"
                except (ValueError, TypeError):
                    numslot = rank_match.group(1)
            
            fru_match = re.search(r'FRU\s+Name\.*:\s+(\S+)', line)
            if fru_match:
                fru_part = fru_match.group(1)
                type_cap_match = re.match(r'(\S+)_(\S+)', fru_part)
                if type_cap_match:
                    mem_type = type_cap_match.group(1)
                    capacity = int(type_cap_match.group(2))
                else:
                    imm_match = re.match(r'(\wIMM)(\S+)', fru_part)
                    if imm_match:
                        ok = True
                        mem_type = imm_match.group(1)
                        numslot = imm_match.group(2)
            
            part_match = re.search(r'Part\s+Number\.*:\s*(\S+)\s+', line)
            if part_match:
                description = part_match.group(1)
            
            serial_match = re.search(r'Serial\s+Number\.*:\s*(\S+)\s+', line)
            if serial_match:
                serialnumber = serial_match.group(1)
                if ok:
                    if capacity == 0:
                        capacity = capacities.get(numslot, 0)
                    memories.append({
                        'CAPACITY': capacity,
                        'DESCRIPTION': f"Part Number {description}" if description else None,
                        'CAPTION': f"Ext {subnumslot} Slot {numslot}",
                        'TYPE': mem_type,
                        'NUMSLOTS': '1',
                        'SERIALNUMBER': serialnumber,
                    })
                    ok = False
                    capacity = 0
        
        return memories
    
    @staticmethod
    def _parse_cstm64(**params) -> List[Dict[str, Any]]:
        """Parse cstm output for Itanium systems."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        memories = []
        
        for line in lines:
            # This pattern assumes memory slots are correctly
            # balanced (slot A and slot B are occupied)
            match = re.match(
                r'(\w+IMM)\s+(\w+)\s+(\d+)'  # first column
                r'\s+'
                r'(\w+IMM)\s+(\w+)\s+(\d+)',  # second column
                line
            )
            if match:
                memories.extend([
                    {
                        'CAPACITY': int(match.group(3)),
                        'DESCRIPTION': match.group(1),
                        'CAPTION': f"{match.group(1)} {match.group(2)}",
                        'TYPE': match.group(1),
                        'NUMSLOTS': match.group(2),
                    },
                    {
                        'CAPACITY': int(match.group(6)),
                        'DESCRIPTION': match.group(4),
                        'CAPTION': f"{match.group(4)} {match.group(5)}",
                        'TYPE': match.group(4),
                        'NUMSLOTS': match.group(5),
                    }
                ])
        
        return memories
