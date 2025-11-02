#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages Adaptec - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_read, get_all_lines, get_canonical_manufacturer
from GLPI.Agent.Tools.Linux import get_devices_from_udev, get_info_from_smartctl


class Adaptec(InventoryModule):
    """Adaptec RAID controller inventory."""
    
    runMeIfTheseChecksFailed = ['GLPI::Agent::Task::Inventory::Linux::Storages']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_read('/proc/scsi/scsi')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        devices = get_devices_from_udev(logger=logger)
        
        for device in devices:
            if not device.get('MANUFACTURER'):
                continue
            if device['MANUFACTURER'] not in ['Adaptec', 'Sun', 'ServeRA']:
                continue
            
            for disk in Adaptec._get_disks_from_proc(
                controller=f"scsi{device.get('SCSI_COID', '')}",
                name=device.get('NAME', ''),
                logger=logger
            ):
                # merge with smartctl info
                info = get_info_from_smartctl(device=disk.get('device'))
                if not info.get('TYPE') or 'disk' not in info['TYPE'].lower():
                    continue
                
                for key in ['SERIALNUMBER', 'DESCRIPTION', 'TYPE', 'DISKSIZE', 'MANUFACTURER']:
                    if key in info:
                        disk[key] = info[key]
                
                if 'device' in disk:
                    del disk['device']
                
                if inventory:
                    inventory.add_entry(section='STORAGES', entry=disk)
    
    @staticmethod
    def _get_disks_from_proc(**params) -> List[Dict[str, Any]]:
        """Get disks from /proc/scsi/scsi."""
        if 'file' not in params:
            params['file'] = '/proc/scsi/scsi'
        
        controller = params.get('controller')
        if not controller:
            return []
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        disks = []
        disk = None
        count = -1
        
        for line in lines:
            host_match = re.match(r'^Host: (\w+)', line)
            if host_match:
                count += 1
                if host_match.group(1) == controller:
                    # that's the controller we're looking for
                    disk = {
                        'NAME': params.get('name', ''),
                    }
                else:
                    # that's another controller
                    disk = None
            
            model_match = re.match(r'Model: \s (\S.+\S) \s+ Rev: \s (\S+)', line, re.VERBOSE)
            if model_match and disk is not None:
                disk['MODEL'] = model_match.group(1)
                disk['FIRMWARE'] = model_match.group(2)
                
                # that's the controller itself, not a disk
                if re.search(r'raid|virtual', disk['MODEL'], re.IGNORECASE):
                    continue
                
                disk['MANUFACTURER'] = get_canonical_manufacturer(disk['MODEL'])
                disk['device'] = f'/dev/sg{count}'
                
                disks.append(disk)
        
        return disks
