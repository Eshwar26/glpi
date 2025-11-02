#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Pacman - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Pacman(InventoryModule):
    """Pacman package inventory module (Arch Linux)."""
    
    MONTHS = {name: idx for idx, name in enumerate([
        '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ], start=0)}
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('pacman')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        packages = Pacman._get_packages_list(
            logger=logger,
            command='pacman -Qqi'
        )
        if not packages:
            return
        
        for package in packages:
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=package
                )
    
    @staticmethod
    def _get_packages_list(**params) -> Optional[List[Dict[str, Any]]]:
        """Get list of Pacman packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        package = None
        
        for line in lines:
            if not line:
                continue
            
            match = re.match(r'^(\S[^:]*):\s*(.*)$', line)
            if not match:
                continue
            
            key, value = match.groups()
            key = key.rstrip()
            
            if key == 'Name':
                if package:
                    packages.append(package)
                package = {'NAME': value}
            
            elif not package:
                continue
            
            elif key == 'Version' and value:
                version = re.sub(r'^\d+:', '', value)
                package['VERSION'] = version
            
            elif key == 'Description' and value:
                package['COMMENTS'] = value
            
            elif key == 'Architecture' and value:
                package['ARCH'] = value
            
            elif key == 'Install Date' and value:
                date_match = re.match(r'^\w+\s+(\w+)\s+(\d+)\s+[\d:]+\s+(\d+)$', value)
                if date_match:
                    month_name, day, year = date_match.groups()
                    month = Pacman.MONTHS.get(month_name)
                    if month:
                        package['INSTALLDATE'] = f"{int(day):02d}/{month:02d}/{year}"
            
            elif key == 'Installed Size' and value:
                size_match = re.match(r'^([\d.]+)\s+(\w+)$', value)
                if size_match:
                    size_val, unit = size_match.groups()
                    size_val = float(size_val)
                    size = int(
                        size_val * 1024 if unit == 'KiB' else
                        size_val * 1048576 if unit == 'MiB' else
                        size_val * 1073741824 if unit == 'GiB' else
                        size_val
                    )
                    package['FILESIZE'] = size
            
            elif key == 'Groups' and value and value != 'None':
                package['SYSTEM_CATEGORY'] = ','.join(value.split())
        
        # Add last software
        if package:
            packages.append(package)
        
        return packages
