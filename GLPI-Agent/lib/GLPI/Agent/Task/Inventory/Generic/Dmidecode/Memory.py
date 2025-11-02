#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Dmidecode Memory - Python Implementation
"""

import re
from typing import Any, Dict, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import get_canonical_speed, get_canonical_size, trim_whitespace, get_sanitized_string, hex2char
from GLPI.Agent.Tools.Generic import get_dmidecode_infos
from GLPI.Agent.Tools.PartNumber import PartNumber


class Memory(InventoryModule):
    """Dmidecode memory inventory module."""
    
    # Run after virtualization to decide if found component is virtual
    run_after_if_enabled = [
        'GLPI.Agent.Task.Inventory.Vmsystem',
        'GLPI.Agent.Task.Inventory.Win32.Hardware',
        'GLPI.Agent.Task.Inventory.Linux.Memory',
        'GLPI.Agent.Task.Inventory.BSD.Memory',
    ]
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "memory"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        memories = Memory._get_memories(logger=logger)
        
        if not memories:
            return
        
        # If only one component is defined and we are under a vmsystem, we can update
        # component capacity to real found size. This permits to support memory size updates.
        vmsystem = inventory.get_hardware('VMSYSTEM')
        if vmsystem and not re.match(r'^(Physical|VMware)$', vmsystem):
            components = [m for m in memories if 'CAPACITY' in m]
            if len(components) == 1:
                real_memory = inventory.get_hardware('MEMORY')
                component = components[0]
                if not real_memory:
                    if logger:
                        logger.debug2("Can't verify real memory capacity on this virtual machine")
                elif not component.get('CAPACITY') or component['CAPACITY'] != real_memory:
                    if logger:
                        if component.get('CAPACITY'):
                            logger.debug2(
                                f"Updating virtual component memory capacity to found real capacity: "
                                f"{component['CAPACITY']} => {real_memory}"
                            )
                        else:
                            logger.debug2(f"Setting virtual component memory capacity to {real_memory}")
                    component['CAPACITY'] = real_memory
        
        for memory in memories:
            if inventory:
                inventory.add_entry(
                    section='MEMORIES',
                    entry=memory
                )
    
    @staticmethod
    def _get_memories(**params) -> Optional[List[Dict[str, Any]]]:
        """Get memory modules from dmidecode."""
        infos = get_dmidecode_infos(**params)
        
        memories = []
        slot = 0
        defaults = {}
        
        bios_infos = infos.get(0, [{}])[0]
        bios_vendor = bios_infos.get('Vendor', '')
        bios_version = bios_infos.get('Version', '')
        
        if re.match(r'^Microsoft', bios_vendor, re.IGNORECASE) and re.match(r'^Hyper-V', bios_version, re.IGNORECASE):
            defaults = {
                'Description': 'Hyper-V Memory',
                'Manufacturer': bios_vendor,
            }
        
        if infos.get(17):
            for info in infos[17]:
                slot += 1
                
                # Flash is 'in general' an unrelated internal BIOS storage
                # See bug: #1334
                if info.get('Type') and re.match(r'Flash', info['Type'], re.IGNORECASE):
                    continue
                
                manufacturer = None
                if info.get('Manufacturer'):
                    # Check if manufacturer is not a placeholder value
                    if not re.search(
                        r'Manufacturer|Undefined|None|^0x|\d{4}|\sDIMM',
                        info['Manufacturer'],
                        re.IGNORECASE | re.VERBOSE
                    ):
                        manufacturer = info['Manufacturer']
                
                memory = {
                    'NUMSLOTS': slot,
                    'DESCRIPTION': info.get('Form Factor') or defaults.get('Description'),
                    'CAPTION': info.get('Locator'),
                    'SPEED': get_canonical_speed(info.get('Speed')),
                    'TYPE': info.get('Type'),
                    'SERIALNUMBER': info.get('Serial Number'),
                    'MEMORYCORRECTION': infos.get(16, [{}])[0].get('Error Correction Type'),
                    'MANUFACTURER': manufacturer or defaults.get('Manufacturer')
                }
                
                if info.get('Size'):
                    match = re.match(r'^(\d+\s*.B)$', info['Size'], re.VERBOSE)
                    if match:
                        memory['CAPACITY'] = get_canonical_size(match.group(1), 1024)
                
                if info.get('Part Number'):
                    # Check if part number is not a placeholder
                    if not re.search(
                        r'DIMM|Part\s*Num|Ser\s*Num',
                        info['Part Number'],
                        re.IGNORECASE | re.VERBOSE
                    ):
                        model = trim_whitespace(
                            get_sanitized_string(hex2char(info['Part Number']))
                        )
                        model = re.sub(r'-+$', '', model)
                        memory['MODEL'] = model
                        
                        partnumber_factory = PartNumber(**params)
                        partnumber = partnumber_factory.match(
                            partnumber=memory['MODEL'],
                            category='memory',
                            mm_id=info.get('Module Manufacturer ID', '')
                        )
                        if partnumber:
                            memory['MANUFACTURER'] = partnumber.manufacturer()
                            if not memory.get('SPEED') and partnumber.speed():
                                memory['SPEED'] = partnumber.speed()
                            if not memory.get('TYPE') and partnumber.type():
                                memory['TYPE'] = partnumber.type()
                
                memories.append(memory)
                
        elif infos.get(6):
            for info in infos[6]:
                slot += 1
                
                memory = {
                    'NUMSLOTS': slot,
                    'TYPE': info.get('Type'),
                }
                
                if info.get('Installed Size'):
                    match = re.match(r'^(\d+\s*.B)', info['Installed Size'], re.IGNORECASE)
                    if match:
                        memory['CAPACITY'] = get_canonical_size(match.group(1), 1024)
                
                memories.append(memory)
        
        return memories if memories else None
