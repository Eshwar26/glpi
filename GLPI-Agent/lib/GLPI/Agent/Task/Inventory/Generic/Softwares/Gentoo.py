#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Gentoo - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_first_match, compare_version


class Gentoo(InventoryModule):
    """Gentoo package inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('equery')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        command = "equery list -i '*'" if Gentoo._equery_needs_wildcard() else "equery list -i"
        
        packages = Gentoo._get_packages_list(
            logger=logger,
            command=command
        )
        
        if packages:
            for package in packages:
                if inventory:
                    inventory.add_entry(
                        section='SOFTWARES',
                        entry=package
                    )
    
    @staticmethod
    def _get_packages_list(**params) -> Optional[List[Dict[str, str]]]:
        """Get list of Gentoo packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        for line in lines:
            match = re.match(r'^(.*)-([0-9]+.*)', line)
            if match:
                packages.append({
                    'NAME': match.group(1),
                    'VERSION': match.group(2),
                })
        
        return packages
    
    @staticmethod
    def _equery_needs_wildcard() -> bool:
        """Check if equery needs wildcard (version >= 0.3)."""
        # http://forge.fusioninventory.org/issues/852
        result = get_first_match(
            command='equery -V',
            pattern=r'^equery ?\((\d+)\.(\d+)\.\d+\)',
        )
        
        if not result:
            return False
        
        major, minor = result if isinstance(result, tuple) else (result, 0)
        
        # True starting from version 0.3
        return compare_version(int(major), int(minor), 0, 3)
