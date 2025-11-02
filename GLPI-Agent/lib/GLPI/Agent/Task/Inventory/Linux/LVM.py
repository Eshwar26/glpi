#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux LVM - Python Implementation
"""

from typing import Any, List, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class LVM(InventoryModule):
    """Linux LVM (Logical Volume Manager) detection module."""
    
    category = "lvm"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lvs')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        for volume in LVM._get_logical_volumes(logger=logger):
            if inventory:
                inventory.add_entry(section='LOGICAL_VOLUMES', entry=volume)
        
        for volume in LVM._get_physical_volumes(logger=logger):
            if inventory:
                inventory.add_entry(section='PHYSICAL_VOLUMES', entry=volume)
        
        for group in LVM._get_volume_groups(logger=logger):
            if inventory:
                inventory.add_entry(section='VOLUME_GROUPS', entry=group)
    
    @staticmethod
    def _get_logical_volumes(**params) -> List[Dict[str, Any]]:
        """Get logical volumes."""
        if 'command' not in params:
            params['command'] = 'lvs -a --noheading --nosuffix --units M -o lv_name,vg_uuid,lv_attr,lv_size,lv_uuid,seg_count'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        volumes = []
        for line in lines:
            infos = line.split()
            if len(infos) < 6:
                continue
            
            volumes.append({
                'LV_NAME': infos[0],
                'VG_UUID': infos[1],
                'ATTR': infos[2],
                'SIZE': int(float(infos[3]) if infos[3] else 0),
                'LV_UUID': infos[4],
                'SEG_COUNT': infos[5],
            })
        
        return volumes
    
    @staticmethod
    def _get_physical_volumes(**params) -> List[Dict[str, Any]]:
        """Get physical volumes."""
        if 'command' not in params:
            params['command'] = 'pvs --noheading --nosuffix --units M -o pv_name,pv_fmt,pv_attr,pv_size,pv_free,pv_uuid,pv_pe_count,vg_uuid'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        volumes = []
        for line in lines:
            infos = line.split()
            if len(infos) < 8:
                continue
            
            pe_size = None
            try:
                if infos[6] and float(infos[6]) > 0:
                    pe_size = int(float(infos[3]) / float(infos[6]))
            except (ValueError, ZeroDivisionError):
                pass
            
            volumes.append({
                'DEVICE': infos[0],
                'FORMAT': infos[1],
                'ATTR': infos[2],
                'SIZE': int(float(infos[3]) if infos[3] else 0),
                'FREE': int(float(infos[4]) if infos[4] else 0),
                'PV_UUID': infos[5],
                'PV_PE_COUNT': infos[6],
                'PE_SIZE': pe_size,
                'VG_UUID': infos[7]
            })
        
        return volumes
    
    @staticmethod
    def _get_volume_groups(**params) -> List[Dict[str, Any]]:
        """Get volume groups."""
        if 'command' not in params:
            params['command'] = 'vgs --noheading --nosuffix --units M -o vg_name,pv_count,lv_count,vg_attr,vg_size,vg_free,vg_uuid,vg_extent_size'
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        groups = []
        for line in lines:
            infos = line.split()
            if len(infos) < 8:
                continue
            
            groups.append({
                'VG_NAME': infos[0],
                'PV_COUNT': infos[1],
                'LV_COUNT': infos[2],
                'ATTR': infos[3],
                'SIZE': int(float(infos[4]) if infos[4] else 0),
                'FREE': int(float(infos[5]) if infos[5] else 0),
                'VG_UUID': infos[6],
                'VG_EXTENT_SIZE': infos[7],
            })
        
        return groups
