#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares RPM - Python Implementation
"""

import time
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class RPM(InventoryModule):
    """RPM package inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('rpm')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        command = (
            "rpm -qa --queryformat '"
            "%{NAME}\t"
            "%{ARCH}\t"
            "%{VERSION}-%{RELEASE}\t"
            "%{INSTALLTIME}\t"
            "%{SIZE}\t"
            "%{VENDOR}\t"
            "%{SUMMARY}\t"
            "%{GROUP}\n"
            "'"
        )
        
        packages = RPM._get_packages_list(logger=logger, command=command)
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
        """Get list of RPM packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        
        for line in lines:
            try:
                # Try to decode as UTF-8
                if isinstance(line, bytes):
                    line = line.decode('utf-8')
            except UnicodeDecodeError:
                continue
            
            infos = line.split('\t')
            if len(infos) < 8:
                continue
            
            package = {
                'NAME': infos[0],
                'ARCH': infos[1],
                'VERSION': infos[2],
                'FILESIZE': infos[4],
                'COMMENTS': infos[6],
                'FROM': 'rpm',
                'SYSTEM_CATEGORY': infos[7]
            }
            
            # Parse install date
            try:
                install_time = int(infos[3])
                time_struct = time.localtime(install_time)
                package['INSTALLDATE'] = time.strftime(
                    "%d/%m/%Y", time_struct
                )
            except (ValueError, OSError):
                pass
            
            if infos[5] and infos[5] != '(none)':
                package['PUBLISHER'] = infos[5]
            
            packages.append(package)
        
        return packages
