#!/usr/bin/env python3
"""
GLPI Agent Task Inventory BSD Softwares - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Softwares(InventoryModule):
    """BSD Softwares inventory module."""
    
    @staticmethod
    def category() -> str:
        """Return the inventory category."""
        return "software"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('pkg_info') or can_run('pkg')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Try pkg_info first, then pkg info
        packages = (
            Softwares._get_packages_list(logger=logger, command='pkg_info') or
            Softwares._get_packages_list(logger=logger, command='pkg info')
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
    def _get_packages_list(**params) -> Optional[List[Dict[str, str]]]:
        """Get list of installed packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        for line in lines:
            # Format: name-version - version description
            match = re.match(r'^(\S+) - (\S+)\s+(.*)', line, re.VERBOSE)
            if match:
                packages.append({
                    'NAME': match.group(1),
                    'VERSION': match.group(2),
                    'COMMENTS': match.group(3)
                })
        
        return packages if packages else None
