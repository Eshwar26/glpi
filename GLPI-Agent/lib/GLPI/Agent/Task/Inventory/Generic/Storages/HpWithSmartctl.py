#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Storages HpWithSmartctl - Python Implementation

This speeds up hpacucli startup by skipping non-local (iSCSI, Fibre) storages.
See https://support.hpe.com/hpsc/doc/public/display?docId=emr_na-c03696601
"""

import os
import re
from typing import Any, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, glob_files, get_all_lines, get_first_match, first
from GLPI.Agent.Tools.Linux import get_info_from_smartctl


# Set environment variable to speed up hpacucli
os.environ['INFOMGR_BYPASS_NONSA'] = '1'


class HpWithSmartctl(InventoryModule):
    """HP RAID controller with smartctl inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return (
            can_run('hpacucli') and
            can_run('smartctl') and
            # TODO: find a generic solution
            bool(glob_files("/sys/class/scsi_generic/sg*/device/vpd_pg80"))
        )
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        adp = HpWithSmartctl._get_data(**params)
        
        for data in adp.values():
            if not (data.get('drives_total') and data.get('device')):
                continue
            
            for i in range(data['drives_total']):
                storage = get_info_from_smartctl(
                    device=f"/dev/{data['device']}",
                    extra=f'-d cciss,{i}',
                    **params
                )
                
                if inventory:
                    inventory.add_entry(
                        section='STORAGES',
                        entry=storage
                    )
    
    @staticmethod
    def _get_data(**params) -> Dict[int, Dict[str, Any]]:
        """Get HP RAID controller data."""
        params = dict(params)
        params['command'] = 'hpacucli ctrl all show config'
        
        data = {}
        slot = -1
        
        for line in get_all_lines(**params):
            # Match controller line
            match = re.match(r'^Smart Array \w+ in Slot (\d+)\s+(?:\(Embedded\)\s+)?\(sn: (\w+)\)', line)
            if match:
                slot_num = int(match.group(1))
                data[slot_num] = {
                    'serial': match.group(2),
                    'drives_total': 0,
                }
                slot = slot_num
            # Match physical drive line (skip failed drives)
            elif re.match(r'^\s+physicaldrive\s', line) and 'Failed' not in line:
                if slot != -1:
                    data[slot]['drives_total'] += 1
        
        HpWithSmartctl._adp_to_device(data)
        
        return data
    
    @staticmethod
    def _adp_to_device(adp: Dict[int, Dict[str, Any]]) -> None:
        """Map adapter to device (Linux case)."""
        for file in glob_files("/sys/class/scsi_generic/sg*/device/vpd_pg80"):
            serial = get_first_match(
                file=file,
                pattern=r'(\w+)'
            )
            if not serial:
                continue
            
            # Find slot matching this serial
            slot = first(
                lambda s: adp[s].get('serial') == serial,
                adp.keys()
            )
            if slot is None:
                continue
            
            # Extract device name from file path
            match = re.search(r'/(sg\d+)/', file)
            if match:
                adp[slot]['device'] = match.group(1)
