#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Flatpak - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, trim_whitespace


class Flatpak(InventoryModule):
    """Flatpak package inventory module."""
    
    MAPPING = {
        'Installed': 'FILESIZE',
        'Version': 'VERSION',
        'Origin': 'PUBLISHER',
        'Arch': 'ARCH',
        'Installation': 'SYSTEM_CATEGORY',
        'Date': 'INSTALLDATE',
    }
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('flatpak')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        packages = Flatpak._get_flatpak_list(logger=logger)
        
        for flatpak in packages:
            flatpak = Flatpak._get_flatpak_info(
                logger=logger,
                flatpak=flatpak,
            )
            if not flatpak:
                continue
            
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=flatpak
                )
    
    @staticmethod
    def _get_flatpak_list(**params) -> List[Dict[str, str]]:
        """Get list of Flatpak applications."""
        apps = []
        
        for line in get_all_lines(
            command='flatpak list -a --columns=application,branch,installation,name',
            **params
        ):
            # Skip header line
            if re.search(r'Application ID.*Name', line):
                continue
            
            match = re.match(r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S.*)$', line)
            if not match:
                continue
            
            appid, branch, mode, name = match.groups()
            
            apps.append({
                '_BRANCH': branch,
                '_APPID': appid,
                'NAME': trim_whitespace(name),
                'SYSTEM_CATEGORY': mode,
                'FROM': 'flatpak'
            })
        
        return apps
    
    @staticmethod
    def _get_flatpak_info(**params) -> Optional[Dict[str, Any]]:
        """Get detailed Flatpak application info."""
        flatpak = params.get('flatpak')
        if not flatpak:
            return None
        
        mode = flatpak.get('SYSTEM_CATEGORY')
        appid = flatpak.pop('_APPID', '')
        branch = flatpak.pop('_BRANCH', '')
        
        # $mode can be "user" or "system"
        infos = get_all_lines(
            command=f'flatpak info --{mode} {appid} {branch}',
            logger=params.get('logger')
        )
        if not infos:
            return None
        
        for info in infos:
            match = re.match(r'(\S+):\s+(.*)$', info)
            if not match:
                continue
            
            key, value = match.groups()
            
            keyname = Flatpak.MAPPING.get(key)
            if not keyname:
                continue
            
            if keyname == 'FILESIZE':
                # Convert size as bytes
                size_match = re.match(r'^([\d.]+).*([kMG]B)$', value)
                if size_match:
                    size, unit = size_match.groups()
                    size = float(size)
                    value = int(
                        size * 1024 if unit == 'kB' else
                        size * 1048576 if unit == 'MB' else
                        size * 1073741824  # unit == "GB"
                    )
                else:
                    continue
            elif keyname == 'INSTALLDATE':
                # Example: Date: 2020-10-04 14:56:29 +0000
                date_match = re.match(r'^(\d+)-(\d+)-(\d+)\s', value)
                if date_match:
                    year, month, day = date_match.groups()
                    value = f"{int(day):02d}/{int(month):02d}/{year}"
                else:
                    continue
            
            if value is not None:
                flatpak[keyname] = value
        
        # Use branch as version if version is not set
        if branch and not flatpak.get('VERSION'):
            flatpak['VERSION'] = branch
        
        # Add AppID as comment
        flatpak['COMMENTS'] = f"AppID: {appid}"
        
        return flatpak
