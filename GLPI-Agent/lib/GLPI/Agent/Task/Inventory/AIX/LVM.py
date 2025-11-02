#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX LVM - Python Implementation
"""

import re
from typing import Dict, Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class LVM(InventoryModule):
    """AIX LVM inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "lvm"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lspv')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Physical volumes
        for volume in LVM._get_physical_volumes(
            command='lspv',
            logger=logger
        ):
            if inventory:
                inventory.add_entry(section='PHYSICAL_VOLUMES', entry=volume)
        
        # Volume groups and logical volumes
        for group in LVM._get_volume_groups(
            command='lsvg',
            logger=logger
        ):
            if inventory:
                inventory.add_entry(section='VOLUME_GROUPS', entry=group)
            
            # Get logical volumes for this group
            vg_name = group.get('VG_NAME')
            if vg_name:
                for volume in LVM._get_logical_volumes(
                    command=f"lsvg -l {vg_name}",
                    logger=logger
                ):
                    if inventory:
                        inventory.add_entry(section='LOGICAL_VOLUMES', entry=volume)
    
    @staticmethod
    def _get_logical_volumes(**params) -> List[Dict[str, Any]]:
        """Get logical volumes."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        # skip headers
        if lines:
            lines = lines[1:]
        
        # no logical volume if there is only one line of output
        if not lines or len(lines) < 1:
            return []
        
        # Skip one more line
        if lines:
            lines = lines[1:]
        
        volumes = []
        logger = params.get('logger')
        
        for line in lines:
            parts = line.split()
            if parts:
                name = parts[0]
                volume = LVM._get_logical_volume(logger=logger, name=name)
                if volume:
                    volumes.append(volume)
        
        return volumes
    
    @staticmethod
    def _get_logical_volume(**params) -> Optional[Dict[str, Any]]:
        """Get single logical volume info."""
        name = params.get('name')
        if not name:
            return None
        
        params['command'] = f"lslv {name}"
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        volume = {
            'LV_NAME': name
        }
        
        size = None
        for line in lines:
            match = re.search(r'PP SIZE:\s+(\d+)', line)
            if match:
                size = int(match.group(1))
            
            match = re.search(r'^LV IDENTIFIER:\s+(\S+)', line)
            if match:
                volume['LV_UUID'] = match.group(1)
            
            match = re.search(r'^LPs:\s+(\S+)', line)
            if match:
                volume['SEG_COUNT'] = int(match.group(1))
            
            match = re.search(r'^TYPE:\s+(\S+)', line)
            if match:
                volume['ATTR'] = f"Type {match.group(1)}"
        
        if 'SEG_COUNT' in volume and size is not None:
            volume['SIZE'] = volume['SEG_COUNT'] * size
        
        return volume
    
    @staticmethod
    def _get_physical_volumes(**params) -> List[Dict[str, Any]]:
        """Get physical volumes."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        volumes = []
        logger = params.get('logger')
        
        for line in lines:
            parts = line.split()
            if parts:
                name = parts[0]
                volume = LVM._get_physical_volume(logger=logger, name=name)
                if volume:
                    volumes.append(volume)
        
        return volumes
    
    @staticmethod
    def _get_physical_volume(**params) -> Optional[Dict[str, Any]]:
        """Get single physical volume info."""
        name = params.get('name')
        if not name:
            return None
        
        params['command'] = f"lspv {name}"
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        volume = {
            'DEVICE': f"/dev/{name}"
        }
        
        free = None
        total = None
        
        for line in lines:
            if re.search(r'PHYSICAL VOLUME:\s+(\S+)', line):
                volume['FORMAT'] = 'AIX PV'
            
            match = re.search(r'FREE PPs:\s+(\d+)', line)
            if match:
                free = int(match.group(1))
            
            match = re.search(r'TOTAL PPs:\s+(\d+)', line)
            if match:
                total = int(match.group(1))
            
            match = re.search(r'VOLUME GROUP:\s+(\S+)', line)
            if match:
                volume['ATTR'] = f"VG {match.group(1)}"
            
            match = re.search(r'PP SIZE:\s+(\d+)', line)
            if match:
                volume['PE_SIZE'] = int(match.group(1))
            
            match = re.search(r'PV IDENTIFIER:\s+(\S+)', line)
            if match:
                volume['PV_UUID'] = match.group(1)
        
        if 'PE_SIZE' in volume:
            if total is not None:
                volume['SIZE'] = total * volume['PE_SIZE']
            if free is not None:
                volume['FREE'] = free * volume['PE_SIZE']
        
        if total is not None:
            volume['PV_PE_COUNT'] = total
        
        return volume
    
    @staticmethod
    def _get_volume_groups(**params) -> List[Dict[str, Any]]:
        """Get volume groups."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        groups = []
        logger = params.get('logger')
        
        for line in lines:
            name = line.strip()
            if name:
                group = LVM._get_volume_group(logger=logger, name=name)
                if group:
                    groups.append(group)
        
        return groups
    
    @staticmethod
    def _get_volume_group(**params) -> Optional[Dict[str, Any]]:
        """Get single volume group info."""
        name = params.get('name')
        if not name:
            return None
        
        params['command'] = f"lsvg {name}"
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        group = {
            'VG_NAME': name
        }
        
        for line in lines:
            match = re.search(r'TOTAL PPs:\s+(\d+)', line)
            if match:
                group['SIZE'] = int(match.group(1))
            
            match = re.search(r'FREE PPs:\s+(\d+)', line)
            if match:
                group['FREE'] = int(match.group(1))
            
            match = re.search(r'VG IDENTIFIER:\s+(\S+)', line)
            if match:
                group['VG_UUID'] = match.group(1)
            
            match = re.search(r'PP SIZE:\s+(\d+)', line)
            if match:
                group['VG_EXTENT_SIZE'] = int(match.group(1))
            
            match = re.search(r'LVs:\s+(\d+)', line)
            if match:
                group['LV_COUNT'] = int(match.group(1))
            
            match = re.search(r'ACTIVE PVs:\s+(\d+)', line)
            if match:
                group['PV_COUNT'] = int(match.group(1))
        
        return group
