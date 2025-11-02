#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Storages - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_line, has_link


class Storages(InventoryModule):
    """Solaris storage devices detection module."""
    
    category = "storage"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('iostat')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        storages = Storages._get_storages(
            logger=logger,
            command='iostat -En'
        )
        
        for storage in storages:
            device_name = storage.get('NAME')
            if device_name and has_link(f"/dev/rdsk/{device_name}s2"):
                rdisk_path = get_first_line(
                    command=f"ls -l /dev/rdsk/{device_name}s2"
                )
                if rdisk_path:
                    if 'scsi_vhci' in rdisk_path:
                        storage['TYPE'] = 'MPxIO'
                    elif 'fp@' in rdisk_path:
                        storage['TYPE'] = 'FC'
                    elif 'scsi@' in rdisk_path:
                        storage['TYPE'] = 'SCSI'
            
            if inventory:
                inventory.add_entry(section='STORAGES', entry=storage)
    
    @staticmethod
    def _get_storages(**params) -> List[Dict[str, Any]]:
        """Parse iostat -En output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        storages = []
        storage = {}
        
        for line in lines:
            # Device name line
            name_match = re.match(r'^(\S+)\s+Soft', line)
            if name_match:
                storage['NAME'] = name_match.group(1)
            
            # Vendor, Product, Revision, Serial No line
            info_match = re.match(
                r'^Vendor:       \s (\S+)          \s+'
                r'Product:      \s (\S.*?\S)      \s+'
                r'Revision:     \s (\S+)          \s+'
                r'Serial \s No: (?:\s (\S*))?',
                line,
                re.VERBOSE
            )
            if info_match:
                storage['MANUFACTURER'] = info_match.group(1)
                storage['MODEL'] = info_match.group(2)
                storage['FIRMWARE'] = info_match.group(3)
                if info_match.group(4):
                    storage['SERIALNUMBER'] = info_match.group(4)
            
            # Disk size
            size_match = re.search(r'<(\d+) bytes', line)
            if size_match:
                storage['DISKSIZE'] = int(int(size_match.group(1)) / (1000 * 1000))
            
            # Last line marker
            if line.startswith('Illegal'):
                # To be removed when SERIALNUMBER will be supported
                if storage.get('SERIALNUMBER'):
                    desc = storage.get('DESCRIPTION', '')
                    storage['DESCRIPTION'] = f"{desc} S/N:{storage['SERIALNUMBER']}" if desc else f"S/N:{storage['SERIALNUMBER']}"
                
                # To be removed when FIRMWARE will be supported
                if storage.get('FIRMWARE'):
                    desc = storage.get('DESCRIPTION', '')
                    storage['DESCRIPTION'] = f"{desc} FW:{storage['FIRMWARE']}" if desc else f"FW:{storage['FIRMWARE']}"
                
                if storage.get('MANUFACTURER'):
                    # Workaround for MANUFACTURER == ATA case
                    manufacturer = storage['MANUFACTURER']
                    model = storage.get('MODEL', '')
                    if manufacturer == 'ATA':
                        ata_match = re.match(r'^(Hitachi|Seagate|INTEL) (.+)', model, re.IGNORECASE)
                        if ata_match:
                            storage['MANUFACTURER'] = ata_match.group(1)
                            storage['MODEL'] = ata_match.group(2)
                    
                    # Drop the (R) from the manufacturer string
                    storage['MANUFACTURER'] = re.sub(r'\(R\)$', '', manufacturer, flags=re.IGNORECASE)
                
                storages.append(storage)
                storage = {}
        
        return storages
