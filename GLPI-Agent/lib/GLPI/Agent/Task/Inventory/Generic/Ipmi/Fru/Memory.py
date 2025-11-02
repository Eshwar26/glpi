#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Ipmi Fru Memory - Python Implementation

Processes DIMMs reported by `ipmitool fru`

Updates MEMORIES section with data from `ipmitool fru`. No new records are added.
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools.IpmiFru import get_ipmi_fru, parse_fru
from GLPI.Agent.Tools.PartNumber import PartNumber


class Memory(InventoryModule):
    """IPMI FRU memory inventory module."""
    
    run_after_if_enabled = [
        'GLPI.Agent.Task.Inventory.Generic.Dmidecode.Memory'
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
        """Perform inventory collection - updates existing MEMORIES section."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        fru = get_ipmi_fru(**params)
        if not fru:
            return
        
        fru_keys = [key for key in fru.keys() if ' DIMM' in key and re.match(r'\d', key)]
        if not fru_keys:
            return
        
        memories = inventory.get_section('MEMORIES') or []
        fields = inventory.get_fields().get('MEMORIES')
        
        for fru_key in fru_keys:
            match = re.match(r'^CPU\s*(\d+)[\s_]+DIMM\s*(\d+)', fru_key)
            if not match:
                continue
            
            cpu, dimm = match.groups()
            
            # Find matching memory entries
            mems = [
                mem for mem in memories
                if re.match(
                    rf'^(PROC|CPU)\s*{re.escape(cpu)}[\s_]+DIMM\s*{dimm}(?:[A-Z])?$',
                    mem.get('CAPTION', '')
                )
            ]
            
            if len(mems) != 1:
                continue
            
            parsed_fru = parse_fru(fru[fru_key], fields)
            
            for field in fields.keys():
                if not parsed_fru.get(field):
                    continue
                
                # Check if we should update this field
                should_update = (
                    not mems[0].get(field) or
                    re.search(
                        r'NOT\s*AVAILABLE|None|Not\s*Specified|O\.E\.M\.|Part\s*Num|Ser\s*Num|Serial\s*Num|Unknown',
                        mems[0][field],
                        re.IGNORECASE | re.VERBOSE
                    )
                )
                
                if not should_update:
                    continue
                
                mems[0][field] = parsed_fru[field]
                
                if field == 'MODEL':
                    partnumber_factory = PartNumber(logger=logger)
                    partnumber = partnumber_factory.match(
                        partnumber=mems[0][field],
                        category='memory',
                    )
                    if partnumber:
                        mems[0]['MANUFACTURER'] = partnumber.manufacturer()
                        if not mems[0].get('SPEED') and partnumber.speed():
                            mems[0]['SPEED'] = partnumber.speed()
                        if not mems[0].get('TYPE') and partnumber.type():
                            mems[0]['TYPE'] = partnumber.type()
