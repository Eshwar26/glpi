"""
GLPI Agent Task Inventory Win32 Storages HP Module

HP-specific storage inventory using HP ACUCLI utility.
"""

import os
import re
from pathlib import Path
from typing import Optional


class HP:
    """HP storage inventory module for Windows"""
    
    @staticmethod
    def is_enabled(logger=None, **params) -> bool:
        """
        Check if module is enabled.
        
        Returns:
            True if HP ACUCLI is installed, False otherwise
        """
        return HP._get_hpacucli_from_registry() is not None
    
    @staticmethod
    def do_inventory(inventory=None, logger=None, **params) -> None:
        """
        Execute the inventory.
        
        Args:
            inventory: Inventory instance
            logger: Logger instance
            **params: Additional parameters
        """
        hpacucli_path = HP._get_hpacucli_from_registry()
        if not hpacucli_path:
            return
        
        # Would call HP inventory function
        # from GLPI.Agent.Tools.Storages.HP import hp_inventory
        # hp_inventory(path=hpacucli_path, inventory=inventory, logger=logger, **params)
        
        if logger:
            logger.debug(f"HP ACUCLI found at: {hpacucli_path}")
    
    @staticmethod
    def _get_hpacucli_from_registry() -> Optional[str]:
        """
        Get HP ACUCLI path from Windows Registry.
        
        Returns:
            Path to hpacucli.exe or None if not found
        """
        try:
            # Would import Windows registry tools
            # from GLPI.Agent.Tools.Win32 import get_registry_value, has_file
            
            # Placeholder for registry access
            # uninstall_string = get_registry_value(
            #     path="HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows/CurrentVersion/Uninstall/HP ACUCLI/UninstallString"
            # )
            uninstall_string = None  # Placeholder
            
            if not uninstall_string:
                return None
            
            # Extract path from uninstall string
            match = re.search(r'(.*\\)hpuninst\.exe', str(uninstall_string))
            if not match:
                return None
            
            hpacucli_path = match.group(1) + 'bin\\hpacucli.exe'
            
            # Check if file exists
            # if not has_file(hpacucli_path):
            #     return None
            
            if not Path(hpacucli_path).is_file():
                return None
            
            return hpacucli_path
            
        except Exception:
            return None
