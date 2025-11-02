#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages - Python Implementation
"""

import os
import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import (
    can_run, can_read, has_folder, has_file, get_first_line, get_all_lines,
    get_first_match, get_canonical_manufacturer, get_pci_device_vendor,
    compare_version, empty
)
from GLPI.Agent.Tools.Generic import get_info_from_smartctl, get_device_capacity
from GLPI.Agent.Tools.Linux import get_devices_from_udev, get_devices_from_proc, get_devices_from_hal, get_hdparm_info


class Storages(InventoryModule):
    """Linux storage device inventory module."""
    
    category = "storage"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.pop('inventory', None)
        
        root = params.get('test_path', '')
        params['root'] = root
        
        for device in Storages._get_devices(**params):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=device)
    
    @staticmethod
    def _get_devices(**params) -> List[Dict[str, Any]]:
        """Get all storage devices with complete information."""
        root = params.get('root', '')
        
        devices = Storages._get_devices_base(**params)
        
        # complete with udev for missing bits, if available
        if has_folder(f"{root}/dev/.udev/db/"):
            udev_devices = {d['NAME']: d for d in get_devices_from_udev(**params)}
            
            for device in devices:
                udev_device = udev_devices.get(device.get('NAME'))
                if udev_device:
                    for key, value in udev_device.items():
                        if key not in device or not device[key]:
                            device[key] = value
        
        # By default, get other info from smartctl and then from hdparm
        default_subs = [get_info_from_smartctl, Storages._get_hdparm_info]
        
        for device in devices:
            info_cache = {}
            
            for field in ['DESCRIPTION', 'DISKSIZE', 'FIRMWARE', 'INTERFACE', 'MANUFACTURER', 'MODEL', 'WWN']:
                subs = default_subs
                
                if field == 'MANUFACTURER':
                    # Try to update manufacturer if set to ATA
                    if device.get(field) and device[field] != 'ATA':
                        continue
                    subs = [get_info_from_smartctl]
                elif field == 'MODEL':
                    # proceed in any case to overwrite MODEL
                    pass
                elif device.get(field):
                    continue
                
                for sub in subs:
                    # get info once for each device
                    if sub not in info_cache:
                        info_cache[sub] = sub(device=f"/dev/{device.get('NAME', '')}", **params)
                    
                    if info_cache[sub] and field in info_cache[sub]:
                        device[field] = info_cache[sub][field]
                        break
        
        for device in devices:
            device['DESCRIPTION'] = Storages._fix_description(
                device.get('NAME'),
                device.get('MANUFACTURER'),
                device.get('DESCRIPTION'),
                device.get('SERIALNUMBER')
            )
            
            if not device.get('MANUFACTURER') or device['MANUFACTURER'] == 'ATA':
                manufacturer = get_canonical_manufacturer(device.get('MODEL', ''))
                if manufacturer and not empty(manufacturer) and manufacturer != device.get('MODEL'):
                    device['MANUFACTURER'] = manufacturer
            elif device.get('MANUFACTURER') and re.match(r'^0x(\w+)$', device['MANUFACTURER']):
                match = re.match(r'^0x(\w+)$', device['MANUFACTURER'])
                vendor = get_pci_device_vendor(id=match.group(1).lower())
                if vendor and vendor.get('name'):
                    device['MANUFACTURER'] = vendor['name']
            
            device_type = device.get('TYPE', '')
            if not device.get('DISKSIZE') and not device_type.startswith('cd'):
                device['DISKSIZE'] = get_device_capacity(
                    device=f"/dev/{device.get('NAME', '')}",
                    **params
                )
            
            if device.get('NAME', '').startswith('nvme'):
                device['INTERFACE'] = 'NVME'
            
            # In some case, serial can't be defined using hdparm
            # Then we can define a serial searching for few specific identifiers
            # But avoid to search S/N for empty removable meaning no disk has been inserted
            if not device.get('SERIALNUMBER'):
                if not (device_type == 'removable' and not device.get('DISKSIZE')):
                    params_copy = params.copy()
                    params_copy['device'] = f"/dev/{device.get('NAME', '')}"
                    sn = Storages._get_disk_identifier(**params_copy) or Storages._get_pv_uuid(**params_copy)
                    if sn:
                        device['SERIALNUMBER'] = sn
        
        # Sort devices by name to keep list ordered and consistent over time
        devices.sort(key=lambda d: d.get('NAME', ''))
        return devices
    
    @staticmethod
    def _get_hdparm_info(**params) -> Optional[Dict]:
        """Get serial & firmware numbers from hdparm, if available."""
        if not Storages._correct_hdparm_available(
            root=params.get('root', ''),
            dump=params.get('dump')
        ):
            return None
        
        return get_hdparm_info(**params)
    
    @staticmethod
    def _get_devices_base(**params) -> List[Dict[str, Any]]:
        """Get basic device list."""
        root = params.get('root', '')
        logger = params.get('logger')
        
        if logger:
            logger.debug("retrieving devices list:")
        
        if has_folder(f"{root}/sys/block"):
            devices = get_devices_from_proc(**params)
            if logger:
                logger.debug_result(
                    action='reading /sys/block content',
                    data=len(devices)
                )
            if devices:
                return devices
        else:
            if logger:
                logger.debug_result(
                    action='reading /sys/block content',
                    status='directory not available'
                )
        
        if (not root and can_run('/usr/bin/lshal')) or (root and has_file(f"{root}/lshal")):
            devices = get_devices_from_hal(**params)
            if logger:
                logger.debug_result(
                    action='running lshal command',
                    data=len(devices)
                )
            if devices:
                return devices
        else:
            if logger:
                logger.debug_result(
                    action='running lshal command',
                    status='command not available'
                )
        
        return []
    
    @staticmethod
    def _fix_description(name: Optional[str], manufacturer: Optional[str],
                        description: Optional[str], serialnumber: Optional[str]) -> str:
        """Fix device description based on name and other attributes."""
        # detected as USB by udev
        if description and 'usb' in description.lower():
            return 'USB'
        
        if name and name.startswith('sd'):  # /dev/sd* are SCSI _OR_ SATA
            if ((manufacturer and 'ATA' in manufacturer) or
                (serialnumber and 'ATA' in serialnumber) or
                (description and 'ATA' in description)):
                return 'SATA'
            else:
                return 'SCSI'
        elif name and name.startswith('sg'):  # "g" stands for Generic SCSI
            return 'SCSI'
        elif name and name.startswith('vd') or (description and 'VIRTIO' in description):
            return 'Virtual'
        else:
            return description if description else 'IDE'
    
    @staticmethod
    def _correct_hdparm_available(**params) -> bool:
        """Check if correct hdparm version is available."""
        params = params.copy()
        params['command'] = 'hdparm -V'
        
        root = params.get('root', '')
        if root:
            params['file'] = f"{root}/hdparm"
            if not has_file(params['file']):
                return False
        
        if not (can_run('hdparm') or params.get('file')):
            return False
        
        if params.get('dump'):
            params['dump']['hdparm'] = get_all_lines(**params)
        
        version_match = get_first_match(
            pattern=r'^hdparm v(\d+)\.(\d+)',
            **params
        )
        if not version_match:
            return False
        
        # Parse major and minor versions
        if isinstance(version_match, tuple):
            major, minor = version_match
        else:
            parts = version_match.split('.')
            major = parts[0] if len(parts) > 0 else '0'
            minor = parts[1] if len(parts) > 1 else '0'
        
        # we need at least version 9.15
        return compare_version(int(major), int(minor), 9, 15)
    
    @staticmethod
    def _get_disk_identifier(**params) -> Optional[str]:
        """Get disk identifier from fdisk."""
        root = params.get('root', '')
        if root:
            params['file'] = f"{root}/fdisk"
            if not os.path.exists(params['file']):
                return None
        else:
            params['command'] = 'fdisk -v'
        
        device = params.get('device')
        if not device or not (can_run('fdisk') or params.get('file')):
            return None
        
        if params.get('dump'):
            params['dump']['fdisk'] = get_all_lines(**params)
        
        # GNU version requires -p flag
        version_line = get_first_line(**params)
        if version_line and version_line.startswith('GNU'):
            params['command'] = f"fdisk -p -l {device}"
        else:
            params['command'] = f"fdisk -l {device}"
        
        if root:
            devname = os.path.basename(device)
            params['file'] = f"{root}/fdisk-{devname}"
            if not has_file(params['file']):
                return None
        elif params.get('dump'):
            devname = os.path.basename(device)
            params['dump'][f'fdisk-{devname}'] = get_all_lines(**params)
        
        identifier = get_first_match(
            pattern=r'^Disk identifier:\s*(?:0x)?(\S+)$',
            i=True,
            **params
        )
        
        return identifier
    
    @staticmethod
    def _get_pv_uuid(**params) -> Optional[str]:
        """Get LVM physical volume UUID."""
        root = params.get('root', '')
        device = params.get('device')
        
        if root:
            devname = os.path.basename(device)
            params['file'] = f"{root}/lvm-{devname}"
            if not has_file(params['file']):
                return None
        
        if not device or not (can_run('lvm') or params.get('file')):
            return None
        
        params['command'] = f'lvm pvdisplay -C -o pv_uuid --noheadings {device}'
        
        if params.get('dump'):
            devname = os.path.basename(device)
            params['dump'][f'lvm-{devname}'] = get_all_lines(**params)
        
        uuid = get_first_match(
            pattern=r'^\s*(\S+)',
            **params
        )
        
        return uuid
