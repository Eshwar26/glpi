#!/usr/bin/env python3
"""
GLPI Agent Storages HP Module - Python Implementation

HP storage inventory module using hpacucli/hpssacli command.
"""

import os
from typing import List, Dict, Optional, Any
import re

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_all_lines, get_canonical_size, get_canonical_manufacturer
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Tools import get_all_lines, get_canonical_size, get_canonical_manufacturer


__all__ = ['hp_inventory']


# This speeds up hpacucli startup by skipping non-local (iSCSI, Fibre) storages.
# See https://support.hpe.com/hpsc/doc/public/display?docId=emr_na-c03696601
os.environ['INFOMGR_BYPASS_NONSA'] = "1"


def hp_inventory(inventory, path: str):
    """
    Run HP storage inventory and add entries to inventory object.
    
    Args:
        inventory: Inventory object to add entries to
        path: Path to hpacucli/hpssacli command
    """
    slots = _get_slots(path=path)
    
    for slot in slots:
        drives = _get_drives(path=path, slot=slot)
        
        for drive in drives:
            storage = _get_storage(path=path, slot=slot, drive=drive)
            
            if storage:
                inventory.add_entry(
                    section='STORAGES',
                    entry=storage
                )


def _get_slots(path: Optional[str] = None, **params) -> List[str]:
    """
    Get list of controller slots.
    
    Args:
        path: Path to hpacucli/hpssacli command
        **params: Additional parameters for get_all_lines
        
    Returns:
        List of slot numbers as strings
    """
    if path and 'command' not in params:
        params['command'] = f"{path} ctrl all show"
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    slots = []
    for line in lines:
        match = re.search(r'Slot (\d+)', line)
        if match:
            slots.append(match.group(1))
    
    return slots


def _get_drives(path: Optional[str] = None, slot: Optional[str] = None, **params) -> List[str]:
    """
    Get list of drives for a controller slot.
    
    Args:
        path: Path to hpacucli/hpssacli command
        slot: Controller slot number
        **params: Additional parameters for get_all_lines
        
    Returns:
        List of drive identifiers
    """
    if path and slot is not None and 'command' not in params:
        params['command'] = f"{path} ctrl slot={slot} pd all show"
    
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    drives = []
    for line in lines:
        match = re.search(r'physicaldrive (\S+)', line)
        if match:
            drives.append(match.group(1))
    
    return drives


def _get_storage(path: Optional[str] = None, slot: Optional[str] = None, 
                drive: Optional[str] = None, **params) -> Optional[Dict[str, Any]]:
    """
    Get storage information for a specific drive.
    
    Args:
        path: Path to hpacucli/hpssacli command
        slot: Controller slot number
        drive: Drive identifier
        **params: Additional parameters for get_all_lines
        
    Returns:
        Dictionary containing storage information
    """
    if path and slot is not None and drive is not None and 'command' not in params:
        params['command'] = f"{path} ctrl slot={slot} pd {drive} show"
    
    lines = get_all_lines(**params)
    if not lines:
        return None
    
    data = {}
    for line in lines:
        match = re.match(r'^\s*(\S[^:]+):\s+(.+)$', line)
        if match:
            key = match.group(1)
            value = match.group(2).rstrip()
            data[key] = value
    
    storage = {
        'DESCRIPTION': data.get('Interface Type'),
        'SERIALNUMBER': data.get('Serial Number'),
        'FIRMWARE': data.get('Firmware Revision')
    }
    
    # Process model
    # Possible models:
    # HP      EG0300FBDBR
    # ATA     WDC WD740ADFD-00
    model = data.get('Model', '')
    model = re.sub(r'^ATA\s+', '', model)
    model = re.sub(r'\s+', ' ', model)
    storage['NAME'] = model
    
    # Split manufacturer and model
    match = re.match(r'^(\S+)\s+(\S+)$', model)
    if match:
        storage['MANUFACTURER'] = get_canonical_manufacturer(match.group(1))
        storage['MODEL'] = match.group(2)
    else:
        storage['MANUFACTURER'] = get_canonical_manufacturer(model)
        storage['MODEL'] = model
    
    # Process size
    if 'Size' in data:
        storage['DISKSIZE'] = get_canonical_size(data['Size'])
    
    # Process type
    drive_type = data.get('Drive Type', '')
    storage['TYPE'] = 'disk' if drive_type == 'Data Drive' else drive_type
    
    return storage


if __name__ == '__main__':
    print("GLPI Agent Storages HP Module")
    print("HP storage inventory module")
