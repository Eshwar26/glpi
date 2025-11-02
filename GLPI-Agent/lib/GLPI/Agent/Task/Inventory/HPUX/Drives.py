#!/usr/bin/env python3
"""
GLPI Agent Task Inventory HPUX Drives - Python Implementation
"""

import re
import struct
from datetime import datetime
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match


class Drives(InventoryModule):
    """HP-UX filesystem/drives detection module."""
    
    category = "drive"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('fstyp') and can_run('bdf')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # get filesystem types
        types = get_all_lines(
            command='fstyp -l',
            logger=logger
        )
        
        # get filesystems for each type
        if types:
            for fs_type in types:
                fs_type = fs_type.strip()
                if not fs_type:
                    continue
                for drive in Drives._get_drives(type=fs_type, logger=logger):
                    if inventory:
                        inventory.add_entry(section='DRIVES', entry=drive)
    
    @staticmethod
    def _get_drives(**params) -> List[Dict[str, Any]]:
        """Get drives for a specific filesystem type."""
        fs_type = params.get('type')
        logger = params.get('logger')
        
        drives = Drives._parse_bdf(
            command=f"bdf -t {fs_type}",
            logger=logger
        )
        
        for drive in drives:
            drive['FILESYSTEM'] = fs_type
            if fs_type == 'vxfs':
                date = Drives._get_vxfs_ctime(drive.get('VOLUMN'), logger)
                if date:
                    drive['CREATEDATE'] = date
        
        return drives
    
    @staticmethod
    def _parse_bdf(**params) -> List[Dict[str, Any]]:
        """Parse bdf output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        drives = []
        
        # skip header
        if lines:
            lines = lines[1:]
        
        device = None
        for line in lines:
            # Try single-line format
            match = re.match(r'^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(\S+)', line)
            if match:
                drives.append({
                    'VOLUMN': match.group(1),
                    'TOTAL': int(match.group(2)),
                    'FREE': int(match.group(3)),
                    'TYPE': match.group(6),
                })
                continue
            
            # Try device-only line (continuation format)
            match = re.match(r'^(\S+)\s*$', line)
            if match:
                device = match.group(1)
                continue
            
            # Try continuation line
            match = re.match(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(\S+)', line)
            if match and device:
                drives.append({
                    'VOLUMN': device,
                    'TOTAL': int(match.group(1)),
                    'FREE': int(match.group(3)),
                    'TYPE': match.group(5),
                })
                device = None
        
        return drives
    
    @staticmethod
    def _get_vxfs_ctime(device: Optional[str], logger=None) -> Optional[str]:
        """Get filesystem creation time by reading binary value directly on the device."""
        if not device:
            return None
        
        # Compute version-dependent read offset
        # Output of 'fstyp' should be something like:
        # $ fstyp -v /dev/vg00/lvol3
        #   vxfs
        #   version: 5
        version_str = get_first_match(
            command=f"fstyp -v {device}",
            logger=logger,
            pattern=r'^version:\s+(\d+)$'
        )
        
        if not version_str:
            if logger:
                logger.error(f"unable to compute offset from fstyp output ({device})")
            return None
        
        try:
            version = int(version_str)
        except (ValueError, TypeError):
            if logger:
                logger.error(f"unable to parse version from fstyp output ({device})")
            return None
        
        offset = None
        if version == 5:
            offset = 8200
        elif version == 6:
            offset = 8208
        elif version == 7:
            offset = 8208
        
        if offset is None:
            if logger:
                logger.error(f"unable to compute offset from fstyp output ({device})")
            return None
        
        # read value
        try:
            with open(device, 'rb') as f:
                f.seek(offset)
                raw = f.read(4)
                if len(raw) != 4:
                    return None
                
                # Convert the 4-byte raw data to long integer
                timestamp = struct.unpack('<L', raw)[0]
                
                # Return a string representation of this timestamp
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y/%m/%d %H:%M:%S')
        except Exception:
            return None
