#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages Lsilogic - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_canonical_manufacturer
from GLPI.Agent.Tools.Linux import get_devices_from_udev, get_info_from_smartctl


class Lsilogic(InventoryModule):
    """LSI Logic RAID controller inventory using mpt-status."""
    
    runMeIfTheseChecksFailed = ['GLPI::Agent::Task::Inventory::Linux::Storages']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('mpt-status')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        devices = get_devices_from_udev(logger=logger)
        
        for device in devices:
            for disk in Lsilogic._get_disk_from_mpt_status(
                name=device.get('NAME', ''),
                logger=logger,
                command=f"mpt-status -n -i {device.get('SCSI_UNID', '')}"
            ):
                # merge with smartctl info
                info = get_info_from_smartctl(device=disk.get('device'))
                for key in ['SERIALNUMBER', 'DESCRIPTION', 'TYPE']:
                    if key in info:
                        disk[key] = info[key]
                
                if 'device' in disk:
                    del disk['device']
                
                if inventory:
                    inventory.add_entry(section='STORAGES', entry=disk)
    
    @staticmethod
    def _get_disk_from_mpt_status(**params) -> List[Dict[str, Any]]:
        """Parse mpt-status output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        disks = []
        for line in lines:
            # Example: phys_id:0 scsi_id:0 vendor:SEAGATE  product_id:ST3300007LC      revision:HPC2 size(GB):300
            match = re.search(
                r'phys_id:(\d+)\s+scsi_id:\d+\s+vendor:\S+\s+product_id:(\S.+\S)\s+revision:(\S+)\s+size\(GB\):(\d+)',
                line,
                re.VERBOSE
            )
            if not match:
                continue
            
            phys_id, model, firmware, size = match.groups()
            
            disk = {
                'NAME': params.get('name', ''),
                'device': f'/dev/sg{phys_id}',
                'MODEL': model,
                'MANUFACTURER': get_canonical_manufacturer(model),
                'FIRMWARE': firmware,
                'DISKSIZE': int(size) * 1024
            }
            
            disks.append(disk)
        
        return disks
