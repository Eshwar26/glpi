#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Memory - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_first_match, get_canonical_size, get_canonical_speed
from GLPI.Agent.Tools.Solaris import get_zone, get_prtdiag_infos, get_smbios


class Memory(InventoryModule):
    """Solaris memory detection module."""
    
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
        
        memory_size = get_first_match(
            command='/usr/sbin/prtconf',
            logger=logger,
            pattern=r'^Memory\ssize:\s+(\S+)'
        )
        
        swap_size = get_first_match(
            command='/usr/sbin/swap -l',
            logger=logger,
            pattern=r'\s+(\d+)$'
        )
        
        if inventory:
            inventory.set_hardware({
                'MEMORY': memory_size,
                'SWAP': swap_size
            })
        
        zone = get_zone()
        
        memories = (Memory._get_memories_prtdiag(**params) if zone == 'global'
                   else Memory._get_zone_allocated_memories(memory_size))
        
        for memory in memories:
            if inventory:
                inventory.add_entry(
                    section='MEMORIES',
                    entry=memory
                )
    
    @staticmethod
    def _get_memories_prtdiag(**params) -> List[Dict[str, Any]]:
        """Get memory information from prtdiag."""
        info = get_prtdiag_infos(**params)
        if not info or not info.get('memories'):
            return []
        
        memories = info['memories']
        
        # Update file to smbios test file for unittest
        if 'smbios' in params:
            params['file'] = params['smbios']
        
        smbios = get_smbios(**params)
        if smbios and smbios.get('SMB_TYPE_MEMDEVICE'):
            try:
                from GLPI.Agent.Tools.PartNumber import PartNumber
                partnumber_factory = PartNumber()
            except ImportError:
                partnumber_factory = None
            
            for memory in memories:
                if not memory.get('NUMSLOTS') is not None:
                    continue
                
                numslot = memory['NUMSLOTS']
                if numslot >= len(smbios['SMB_TYPE_MEMDEVICE']):
                    continue
                
                module = smbios['SMB_TYPE_MEMDEVICE'][numslot]
                if not module:
                    continue
                
                if module.get('Memory Type'):
                    mem_type = module['Memory Type']
                    # Parse format like "26 (DDR4)"
                    match = re.match(r'^ \d+ \s+ \( (.*) \) $', mem_type, re.VERBOSE)
                    if match:
                        memory['TYPE'] = match.group(1)
                    else:
                        memory['TYPE'] = mem_type
                
                if module.get('Part Number'):
                    memory['MODEL'] = module['Part Number']
                
                if module.get('Location Tag'):
                    memory['CAPTION'] = module['Location Tag']
                
                if module.get('Size'):
                    memory['CAPACITY'] = get_canonical_size(module['Size'], 1024)
                
                if module.get('Speed'):
                    memory['SPEED'] = get_canonical_speed(module['Speed'])
                
                if module.get('Serial Number') and not re.match(r'^0+$', module['Serial Number']):
                    memory['SERIALNUMBER'] = module['Serial Number']
                
                if module.get('Manufacturer'):
                    manufacturer = module['Manufacturer']
                    match = re.match(r'^8([0-9A-F])([0-9A-F]{2})$', manufacturer, re.IGNORECASE)
                    if match and partnumber_factory:
                        mmid = f"Bank {int(match.group(1), 16) + 1}, Hex 0x{match.group(2).upper()}"
                        try:
                            partnumber = partnumber_factory.match(
                                partnumber=module.get('Part Number'),
                                category='memory',
                                mm_id=mmid
                            )
                            if partnumber:
                                memory['MANUFACTURER'] = partnumber.manufacturer()
                                if not memory.get('SPEED') and partnumber.speed():
                                    memory['SPEED'] = partnumber.speed()
                                if not memory.get('TYPE') and partnumber.type():
                                    memory['TYPE'] = partnumber.type()
                        except Exception:
                            pass
        
        return memories
    
    @staticmethod
    def _get_zone_allocated_memories(size: str) -> List[Dict[str, Any]]:
        """Get memory information for Solaris zones."""
        memories = []
        
        # Just format one virtual memory slot with the detected memory size
        memories.append({
            'DESCRIPTION': 'Allocated memory',
            'CAPTION': 'Shared memory',
            'NUMSLOTS': 1,
            'CAPACITY': size
        })
        
        return memories
