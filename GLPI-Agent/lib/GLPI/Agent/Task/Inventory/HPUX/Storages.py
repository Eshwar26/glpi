#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Storages - Python Implementation
"""

import re
from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match


class Storages(InventoryModule):
    """HP-UX storage devices detection module."""
    
    category = "storage"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('ioscan')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for disk in Storages._get_disks(logger):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=disk)
        
        for tape in Storages._get_tapes(logger):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=tape)
    
    @staticmethod
    def _get_disks(logger=None) -> List[Dict[str, Any]]:
        """Get disk devices."""
        disks = []
        for device in Storages._parse_ioscan(
            command='ioscan -kFnC disk',
            logger=logger
        ):
            # skip alternate links
            is_alternate = get_first_match(
                command=f"pvdisplay {device['NAME']}",
                pattern=rf"{re.escape(device['NAME'])}\.+lternate"
            )
            if is_alternate:
                continue
            
            lines = get_all_lines(
                command=f"diskinfo -v {device['NAME']}",
                logger=logger
            )
            if lines:
                for line in lines:
                    size_match = re.match(r'^\s+size:\s+(\S+)', line)
                    if size_match:
                        try:
                            device['DISKSIZE'] = int(int(size_match.group(1)) / 1024)
                        except (ValueError, TypeError):
                            pass
                    
                    rev_match = re.match(r'^\s+rev level:\s+(\S+)', line)
                    if rev_match:
                        device['FIRMWARE'] = rev_match.group(1)
            
            device['TYPE'] = 'disk'
            disks.append(device)
        
        return disks
    
    @staticmethod
    def _get_tapes(logger=None) -> List[Dict[str, Any]]:
        """Get tape devices."""
        tapes = []
        for device in Storages._parse_ioscan(
            command='ioscan -kFnC tape',
            logger=logger
        ):
            device['TYPE'] = 'tape'
            tapes.append(device)
        
        return tapes
    
    @staticmethod
    def _parse_ioscan(**params) -> List[Dict[str, Any]]:
        """Parse ioscan output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        devices = []
        description = None
        model = None
        manufacturer = None
        
        for line in lines:
            if re.match(r'^\s+(\S+)', line):
                # Device name line
                match = re.match(r'^\s+(\S+)', line)
                if match:
                    device_name = match.group(1)
                    devices.append({
                        'MANUFACTURER': manufacturer,
                        'MODEL': model,
                        'NAME': device_name,
                        'DESCRIPTION': description,
                    })
            else:
                # Info line
                infos = line.split(':')
                if infos:
                    description = infos[0]
                    if len(infos) > 17:
                        # Parse manufacturer and model from field 17
                        match = re.match(r'^(\S+) \s+ (\S.*\S)$', infos[17], re.VERBOSE)
                        if match:
                            manufacturer = match.group(1)
                            model = match.group(2)
        
        return devices
