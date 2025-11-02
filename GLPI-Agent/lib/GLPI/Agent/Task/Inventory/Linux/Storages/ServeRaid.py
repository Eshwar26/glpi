#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages ServeRaid - Python Implementation

Tested on 2.6.* kernels
Cards tested: IBM ServeRAID-6M, IBM ServeRAID-6i
"""

import re
from typing import Any

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_canonical_manufacturer


class ServeRaid(InventoryModule):
    """IBM ServeRAID controller inventory."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ipssend')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        lines = get_all_lines(
            logger=logger,
            command='ipssend GETVERSION'
        )
        if not lines:
            return
        
        for line in lines:
            # Example Output:
            # Found 1 IBM ServeRAID controller(s).
            # ServeRAID Controller Number 1
            #   Controller type                : ServeRAID-6M
            match = re.search(r'ServeRAID Controller Number\s(\d*)', line)
            if not match:
                continue
            
            slot = match.group(1)
            
            config_lines = get_all_lines(
                logger=logger,
                command=f'ipssend GETCONFIG {slot} PD'
            )
            if not config_lines:
                continue
            
            storage = {}
            for line2 in config_lines:
                # Example Output:
                #   Channel #1:
                #      Target on SCSI ID 0
                #         Device is a Hard disk
                #         Size (in MB)/(in sectors): 34715/71096368
                #         Device ID                : IBM-ESXSCBR036C3DFQDB2Q6CDKM
                #         FRU part number          : 32P0729
                
                size_match = re.search(r'Size.*:\s(\d*)/(\d*)', line2)
                if size_match:
                    storage['DISKSIZE'] = int(size_match.group(1))
                
                device_id_match = re.search(r'Device ID.*:\s(.*)', line2)
                if device_id_match:
                    storage['SERIALNUMBER'] = device_id_match.group(1).strip()
                
                fru_match = re.search(r'FRU part number.*:\s(.*)', line2)
                if fru_match:
                    storage['MODEL'] = fru_match.group(1).strip()
                    storage['MANUFACTURER'] = get_canonical_manufacturer(
                        storage.get('SERIALNUMBER', '')
                    )
                    storage['NAME'] = f"{storage['MANUFACTURER']} {storage['MODEL']}"
                    storage['DESCRIPTION'] = 'SCSI'
                    storage['TYPE'] = 'disk'
                    
                    if inventory:
                        inventory.add_entry(section='STORAGES', entry=storage)
                    storage = {}
