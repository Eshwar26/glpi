#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Drives - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match, get_last_line, trim_whitespace, Glob, get_first_line, month
from GLPI.Agent.Tools.Unix import get_filesystems_from_df


class Drives(InventoryModule):
    """Linux filesystem/drives detection module."""
    
    category = "drive"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('df') or can_run('lshal')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for filesystem in Drives._get_filesystems(logger):
            if inventory:
                inventory.add_entry(
                    section='DRIVES',
                    entry=filesystem
                )
    
    @staticmethod
    def _get_filesystems(logger=None) -> List[Dict[str, Any]]:
        """Get filesystems list with details."""
        # Get filesystems list excluding virtual filesystems and Docker overlay
        filesystems = []
        for fs in get_filesystems_from_df(logger=logger, command='df -P -T -k'):
            filesystem = fs.get('FILESYSTEM', '')
            volumn = fs.get('VOLUMN', '')
            if re.match(r'^(tmpfs|devtmpfs|usbfs|proc|devpts|devshm|udev)$', filesystem):
                continue
            if re.match(r'^overlay$', volumn):
                continue
            filesystems.append(fs)
        
        # Get additional information from blkid if available
        if can_run('blkid'):
            for filesystem in filesystems:
                volumn = filesystem.get('VOLUMN')
                if volumn:
                    serial = get_first_match(
                        logger=logger,
                        command=f'blkid -w /dev/null {volumn}',
                        pattern=r'\sUUID="(\S*)"\s'
                    )
                    if serial:
                        filesystem['SERIAL'] = serial
        
        # Attempt to get details with filesystem-dependent utilities
        has_dumpe2fs = can_run('dumpe2fs')
        has_xfs_db = can_run('xfs_db')
        has_fatlabel = can_run('fatlabel')
        has_dosfslabel = False if has_fatlabel else can_run('dosfslabel')
        
        for filesystem in filesystems:
            fs_type = filesystem.get('FILESYSTEM', '')
            volumn = filesystem.get('VOLUMN', '')
            
            # Handle ext2/3/4 filesystems
            if re.match(r'^ext(2|3|4|4dev)', fs_type) and has_dumpe2fs:
                lines = get_all_lines(
                    logger=logger,
                    command=f'dumpe2fs -h {volumn}'
                )
                if lines:
                    for line in lines:
                        uuid_match = re.match(r'Filesystem UUID:\s+(\S+)', line)
                        if uuid_match and not filesystem.get('SERIAL'):
                            filesystem['SERIAL'] = uuid_match.group(1)
                        
                        date_match = re.match(r'Filesystem created:\s+\w+\s+(\w+)\s+(\d+)\s+([\d:]+)\s+(\d{4})$', line)
                        if date_match:
                            mon, day, time, year = date_match.groups()
                            m = month(mon)
                            if m:
                                filesystem['CREATEDATE'] = f"{year}/{m:02d}/{int(day):02d} {time}"
                        
                        label_match = re.match(r'Filesystem volume name:\s*(\S.*)', line)
                        if label_match:
                            label = label_match.group(1)
                            if label != '<none>':
                                filesystem['LABEL'] = label
                continue
            
            # Handle XFS filesystems
            if fs_type == 'xfs' and has_xfs_db:
                if not filesystem.get('SERIAL'):
                    serial = get_first_match(
                        logger=logger,
                        command=f'xfs_db -r -c uuid {volumn}',
                        pattern=r'^UUID =\s+(\S+)'
                    )
                    if serial:
                        filesystem['SERIAL'] = serial
                
                label = get_first_match(
                    logger=logger,
                    command=f'xfs_db -r -c label {volumn}',
                    pattern=r'^label =\s+"(\S+)"'
                )
                if label:
                    filesystem['LABEL'] = label
                continue
            
            # Handle VFAT filesystems
            if fs_type == 'vfat' and (has_fatlabel or has_dosfslabel):
                cmd = 'fatlabel' if has_fatlabel else 'dosfslabel'
                label = get_last_line(
                    logger=logger,
                    command=f'{cmd} {volumn}'
                )
                # Keep label only if last line starts with a non-space character
                if label and re.match(r'^\S', label):
                    filesystem['LABEL'] = trim_whitespace(label)
                continue
        
        # Complete with hal if available
        if can_run('lshal'):
            hal_filesystems = Drives._get_filesystems_from_hal()
            hal_filesystems_map = {fs['VOLUMN']: fs for fs in hal_filesystems if fs.get('VOLUMN')}
            
            for filesystem in filesystems:
                hal_filesystem = hal_filesystems_map.get(filesystem.get('VOLUMN'))
                if hal_filesystem:
                    for key, value in hal_filesystem.items():
                        if not filesystem.get(key):
                            filesystem[key] = value
        
        # Complete with encryption status if available
        if can_run('dmsetup') and can_run('cryptsetup'):
            devicemapper = {}
            cryptsetup = {}
            
            for filesystem in filesystems:
                volumn = filesystem.get('VOLUMN')
                if not volumn:
                    continue
                
                # Find dmsetup uuid if available
                uuid = get_first_match(
                    logger=logger,
                    command=f'dmsetup info {volumn}',
                    pattern=r'^UUID\s*:\s*(.*)$'
                )
                if not uuid:
                    continue
                
                # Find real devicemapper block name
                if uuid not in devicemapper:
                    for uuidfile in Glob('/sys/block/*/dm/uuid'):
                        file_uuid = get_first_line(file=uuidfile)
                        if file_uuid == uuid:
                            dm_match = re.match(r'^(/sys/block/[^/]+)', uuidfile)
                            if dm_match:
                                devicemapper[uuid] = dm_match.group(1)
                                break
                
                if uuid not in devicemapper:
                    continue
                
                # Lookup for crypto devicemapper slaves
                names = []
                for name_file in Glob(f"{devicemapper[uuid]}/slaves/*/dm/name"):
                    name = get_first_line(file=name_file)
                    if name:
                        names.append(name)
                
                # Finally we may try on the device itself
                names.append(volumn)
                
                for name in names:
                    # Check cryptsetup status for the found slave/device
                    if name not in cryptsetup:
                        lines = get_all_lines(command=f'cryptsetup status {name}')
                        if lines:
                            cryptsetup[name] = {}
                            for line in lines:
                                match = re.match(r'^\s*(.*):\s*(.*)$', line)
                                if match:
                                    cryptsetup[name][match.group(1).upper()] = match.group(2)
                    
                    if name not in cryptsetup:
                        continue
                    
                    # Add cryptsetup status to filesystem
                    filesystem['ENCRYPT_NAME'] = cryptsetup[name].get('TYPE')
                    filesystem['ENCRYPT_STATUS'] = 'Yes'
                    filesystem['ENCRYPT_ALGO'] = cryptsetup[name].get('CIPHER')
                    break
        
        return filesystems
    
    @staticmethod
    def _get_filesystems_from_hal() -> List[Dict[str, Any]]:
        """Get filesystems from HAL."""
        return Drives._parse_lshal(command='lshal')
    
    @staticmethod
    def _parse_lshal(**params) -> List[Dict[str, Any]]:
        """Parse lshal output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        devices = []
        device = {}
        
        for line in lines:
            if re.match(r"^udi = '/org/freedesktop/Hal/devices/(volume|block)", line):
                device = {}
                continue
            
            if device is None:
                continue
            
            if re.match(r'^$', line):
                if device.get('ISVOLUME'):
                    del device['ISVOLUME']
                    devices.append(device)
                device = None
            elif re.search(r'^\s+ block.device \s = \s \'([^\']+)\'', line, re.VERBOSE):
                match = re.search(r"'([^']+)'", line)
                if match:
                    device['VOLUMN'] = match.group(1)
            elif re.search(r'^\s+ volume.fstype \s = \s \'([^\']+)\'', line, re.VERBOSE):
                match = re.search(r"'([^']+)'", line)
                if match:
                    device['FILESYSTEM'] = match.group(1)
            elif re.search(r'^\s+ volume.label \s = \s \'([^\']+)\'', line, re.VERBOSE):
                match = re.search(r"'([^']+)'", line)
                if match:
                    device['LABEL'] = match.group(1)
            elif re.search(r'^\s+ volume.uuid \s = \s \'([^\']+)\'', line, re.VERBOSE):
                match = re.search(r"'([^']+)'", line)
                if match:
                    device['SERIAL'] = match.group(1)
            elif re.search(r'^\s+ storage.model \s = \s \'([^\']+)\'', line, re.VERBOSE):
                match = re.search(r"'([^']+)'", line)
                if match:
                    device['TYPE'] = match.group(1)
            elif re.search(r'^\s+ volume.size \s = \s (\S+)', line, re.VERBOSE):
                match = re.search(r'= \s (\S+)', line, re.VERBOSE)
                if match:
                    try:
                        value = int(match.group(1))
                        device['TOTAL'] = int(value / (1024 * 1024) + 0.5)
                    except (ValueError, TypeError):
                        pass
            elif re.search(r'block.is_volume\s*=\s*true', line, re.IGNORECASE):
                device['ISVOLUME'] = True
        
        return devices
