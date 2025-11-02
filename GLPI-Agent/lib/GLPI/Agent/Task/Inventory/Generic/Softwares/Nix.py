#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Softwares Nix - Python Implementation
"""

import re
from typing import Any, List, Dict, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines


class Nix(InventoryModule):
    """Nix package inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('nix-store')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        command = 'nix-store --gc --print-live'
        packages = Nix._get_packages_list(
            logger=logger,
            command=command
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
        """Get list of Nix packages."""
        lines = get_all_lines(**params)
        if not lines:
            return None
        
        packages = []
        seen = set()
        
        for line in lines:
            match = re.match(r'^/nix/store/[^-]+-(.+)-(\d+(?:\.\d+)*)$', line)
            if not match:
                continue
            
            name, version = match.groups()
            
            package = {
                'NAME': name,
                'VERSION': version,
                'FROM': 'nix'
            }
            
            key = f"{name}-{version}"
            if key in seen:
                continue
            seen.add(key)
            
            packages.append(package)
        
        return packages
