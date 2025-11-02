#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Solaris Drives - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_line
from GLPI.Agent.Tools.Unix import get_filesystems_from_df


class Drives(InventoryModule):
    """Solaris filesystem/drives detection module."""
    
    category = "drive"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('df')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        df_version = params.get('df_version')
        if not df_version:
            df_version = get_first_line(logger=logger, command='df --version')
        
        # get filesystems list
        # df --help is on STDERR on some system, so line may be None
        command = 'df -P -k' if df_version and 'GNU' in df_version else 'df -k'
        
        # Get all filesystems
        filesystems = get_filesystems_from_df(command=command, **params)
        
        # Exclude solaris 10 specific devices and cdrom mounts
        filesystems = [
            fs for fs in filesystems
            if not (fs.get('VOLUMN', '').startswith(('/devices', '/platform')) or
                   fs.get('TYPE', '') == 'cdrom')
        ]
        
        # Get indexed list of filesystems types
        mount_res = params.get('mount_res')
        if mount_res:
            mount_lines = get_all_lines(logger=logger, file=mount_res)
        else:
            mount_lines = get_all_lines(logger=logger, command='/usr/sbin/mount -v')
        
        filesystems_types = {}
        if mount_lines:
            for line in mount_lines:
                # Parse format: "<device> on <mountpoint> type <fstype>"
                import re
                match = re.match(r'^(\S+) on \S+ type (\w+)', line)
                if match:
                    filesystems_types[match.group(1)] = match.group(2)
        
        # Set filesystem type based on that information
        for filesystem in filesystems:
            volumn = filesystem.get('VOLUMN')
            if volumn == 'swap':
                filesystem['FILESYSTEM'] = 'swap'
            elif volumn in filesystems_types:
                filesystem['FILESYSTEM'] = filesystems_types[volumn]
        
        # Add filesystems to the inventory
        for filesystem in filesystems:
            # Skip if filesystem is lofs
            if filesystem.get('FILESYSTEM') == 'lofs':
                continue
            if inventory:
                inventory.add_entry(
                    section='DRIVES',
                    entry=filesystem
                )
