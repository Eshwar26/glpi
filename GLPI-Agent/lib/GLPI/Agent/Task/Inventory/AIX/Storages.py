#!/usr/bin/env python3
"""
GLPI Agent Task Inventory AIX Storages - Python Implementation
"""

import re
from typing import Dict, Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match, get_last_line
from GLPI.Agent.Tools.AIX import get_lsvpd_infos


class Storages(InventoryModule):
    """AIX Storages inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "storage"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('lsdev') and can_run('lsattr')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # index VPD infos by AX field
        infos = Storages._get_indexed_lsvpd_infos(logger=logger)
        
        # SCSI disks
        for disk in Storages._get_disks(logger=logger, subclass='scsi', infos=infos):
            disk['DISKSIZE'] = Storages._get_capacity(disk.get('NAME'), logger)
            serial = get_first_match(
                command=f"lscfg -p -v -s -l {disk.get('NAME')}",
                logger=logger,
                pattern=r'Serial Number\.*(.*)' 
            )
            if serial:
                disk['SERIAL'] = serial
            
            if inventory:
                inventory.add_entry(section='STORAGES', entry=disk)
        
        # FCP disks
        for disk in Storages._get_disks(logger=logger, subclass='fcp', infos=infos):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=disk)
        
        # FDAR disks
        for disk in Storages._get_disks(logger=logger, subclass='fdar', infos=infos):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=disk)
        
        # SAS disks
        for disk in Storages._get_disks(logger=logger, subclass='sas', infos=infos):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=disk)
        
        # VSCSI disks (virtual)
        for disk in Storages._get_disks(logger=logger, subclass='vscsi', infos=infos):
            disk['DISKSIZE'] = Storages._get_virtual_capacity(
                name=disk.get('NAME'),
                logger=logger
            )
            disk['MANUFACTURER'] = 'VIO Disk'
            disk['MODEL'] = 'Virtual Disk'
            
            if inventory:
                inventory.add_entry(section='STORAGES', entry=disk)
        
        # CD-ROMs
        for cdrom in Storages._get_cdroms(logger=logger, infos=infos):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=cdrom)
        
        # Tapes
        for tape in Storages._get_tapes(logger=logger, infos=infos):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=tape)
        
        # Floppies
        for floppy in Storages._get_floppies(logger=logger, infos=infos):
            if inventory:
                inventory.add_entry(section='STORAGES', entry=floppy)
    
    @staticmethod
    def _get_indexed_lsvpd_infos(**params) -> Dict[str, Dict[str, Any]]:
        """Get VPD infos indexed by AX field."""
        infos_list = get_lsvpd_infos(**params)
        
        infos = {}
        for info in infos_list:
            ax = info.get('AX')
            if ax:
                infos[ax] = info
        
        return infos
    
    @staticmethod
    def _get_disks(**params) -> List[Dict[str, Any]]:
        """Get disk devices."""
        subclass = params.get('subclass')
        command = f"lsdev -Cc disk -s {subclass} -F 'name:description'" if subclass else None
        
        disks = Storages._parse_lsdev(
            command=command,
            pattern=r'^(.+):(.+)',
            **params
        )
        
        infos = params.get('infos', {})
        for disk in disks:
            disk['TYPE'] = 'disk'
            
            name = disk.get('NAME')
            if name and name in infos:
                info = infos[name]
                disk['MANUFACTURER'] = Storages._get_manufacturer(info)
                disk['MODEL'] = Storages._get_model(info)
        
        return disks
    
    @staticmethod
    def _get_cdroms(**params) -> List[Dict[str, Any]]:
        """Get CD-ROM devices."""
        cdroms = Storages._parse_lsdev(
            command="lsdev -Cc cdrom -s scsi -F 'name:description:status'",
            pattern=r'^(.+):(.+):.+Available.+',
            **params
        )
        
        logger = params.get('logger')
        infos = params.get('infos', {})
        
        for cdrom in cdroms:
            cdrom['TYPE'] = 'cd'
            name = cdrom.get('NAME')
            if name:
                cdrom['DISKSIZE'] = Storages._get_capacity(name, logger)
            
            if name and name in infos:
                info = infos[name]
                cdrom['MANUFACTURER'] = Storages._get_manufacturer(info)
                cdrom['MODEL'] = Storages._get_model(info)
        
        return cdroms
    
    @staticmethod
    def _get_tapes(**params) -> List[Dict[str, Any]]:
        """Get tape devices."""
        tapes = Storages._parse_lsdev(
            command="lsdev -Cc tape -s scsi -F 'name:description:status'",
            pattern=r'^(.+):(.+):.+Available.+',
            **params
        )
        
        logger = params.get('logger')
        infos = params.get('infos', {})
        
        for tape in tapes:
            tape['TYPE'] = 'tape'
            name = tape.get('NAME')
            if name:
                tape['DISKSIZE'] = Storages._get_capacity(name, logger)
            
            if name and name in infos:
                info = infos[name]
                tape['MANUFACTURER'] = Storages._get_manufacturer(info)
                tape['MODEL'] = Storages._get_model(info)
        
        return tapes
    
    @staticmethod
    def _get_floppies(**params) -> List[Dict[str, Any]]:
        """Get floppy devices."""
        floppies = Storages._parse_lsdev(
            command="lsdev -Cc diskette -F 'name:description:status'",
            pattern=r'^(.+):(.+):.+Available.+',
            **params
        )
        
        for floppy in floppies:
            floppy['TYPE'] = 'floppy'
        
        return floppies
    
    @staticmethod
    def _parse_lsdev(**params) -> List[Dict[str, Any]]:
        """Parse lsdev command output."""
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        pattern = params.get('pattern')
        if not pattern:
            return []
        
        devices = []
        for line in lines:
            match = re.match(pattern, line)
            if match:
                devices.append({
                    'NAME': match.group(1),
                    'DESCRIPTION': match.group(2)
                })
        
        return devices
    
    @staticmethod
    def _get_capacity(device: Optional[str], logger) -> Optional[str]:
        """Get device capacity."""
        if not device:
            return None
        
        return get_last_line(
            command=f"lsattr -EOl {device} -a 'size_in_mb'",
            logger=logger
        )
    
    @staticmethod
    def _get_virtual_capacity(**params) -> Optional[str]:
        """Get virtual disk capacity."""
        name = params.get('name')
        command = f"lspv {name}" if name else None
        
        capacity = get_first_match(
            command=command,
            file=params.get('file'),
            pattern=r'TOTAL PPs: +\d+ \((\d+) megabytes\)',
            logger=params.get('logger')
        )
        
        return capacity
    
    @staticmethod
    def _get_manufacturer(device: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get device manufacturer."""
        if not device:
            return None
        
        mf = device.get('MF')
        fn = device.get('FN')
        
        if not mf:
            return None
        
        if fn:
            return f"{mf},FRU number :{fn}"
        else:
            return mf
    
    @staticmethod
    def _get_model(device: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get device model."""
        if not device:
            return None
        
        return device.get('TM')
