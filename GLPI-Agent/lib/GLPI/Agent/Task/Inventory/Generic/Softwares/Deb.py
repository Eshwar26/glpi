#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Deb - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match


class Deb(InventoryModule):
    """Debian package inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('dpkg-query')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        command = (
            "dpkg-query --show --showformat='"
            "${Package}\t"
            "${Architecture}\t"
            "${Version}\t"
            "${Installed-Size}\t"
            "${Section}\t"
            "${Status}\n"
            "'"
        )
        
        packages = Deb._get_packages_list(logger=logger, command=command)
        if not packages:
            return
        
        # Mimic RPM inventory behaviour, as GLPI aggregates software
        # based on name and publisher
        publisher = get_first_match(
            logger=logger,
            pattern=r'^Distributor ID:\s(.+)',
            command='lsb_release -i',
        )
        
        for package in packages:
            package['PUBLISHER'] = publisher
            if inventory:
                inventory.add_entry(
                    section='SOFTWARES',
                    entry=package
                )
    
    @staticmethod
    def _get_packages_list(**params) -> Optional[List[Dict[str, Any]]]:
        """Get list of Debian packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        logger = params.get('logger')
        
        for line in lines:
            # Skip descriptions
            if line.startswith(' '):
                continue
            
            infos = line.split('\t')
            
            # Only keep as installed package if status matches
            if len(infos) > 5 and infos[5] and not re.search(r' installed$', infos[5]):
                if logger:
                    logger.debug(
                        f"Skipping {infos[0]} package as not installed, status='{infos[5]}'"
                    )
                continue
            
            filesize = 0
            if len(infos) > 3 and infos[3].isdigit():
                filesize = int(infos[3]) * 1024
            
            packages.append({
                'NAME': infos[0] if len(infos) > 0 else '',
                'ARCH': infos[1] if len(infos) > 1 else '',
                'VERSION': infos[2] if len(infos) > 2 else '',
                'FILESIZE': filesize,
                'FROM': 'deb',
                'SYSTEM_CATEGORY': infos[4] if len(infos) > 4 else ''
            })
        
        return packages
