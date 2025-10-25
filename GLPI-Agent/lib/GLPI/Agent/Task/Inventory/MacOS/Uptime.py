"""
GLPI Agent Task Inventory MacOS Uptime Module

This module collects system uptime information on macOS systems.
"""

import re
import time
import subprocess
from typing import Optional


class Uptime:
    """MacOS Uptime inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "hardware"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the uptime inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        arch = self._uname("-m")
        boottime = self._get_boot_time(logger=logger)
        
        if not boottime:
            return
        
        uptime = int(time.time()) - boottime
        
        inventory.set_hardware({
            'DESCRIPTION': f"{arch}/{uptime}"
        })
    
    def _get_boot_time(self, **params):
        """
        Get the system boot time.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            int: Boot time as Unix timestamp, or None
        """
        logger = params.get('logger')
        
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'kern.boottime'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Match patterns like "{ sec = 1234567890, usec = 0 }" or just "1234567890"
                match = re.search(r'(?:sec = (\d+)|(\d+)$)', output)
                if match:
                    return int(match.group(1) or match.group(2))
        except Exception as e:
            if logger:
                logger.debug(f"Error getting boot time: {e}")
        
        return None
    
    def _uname(self, flag):
        """
        Execute uname command with given flag.
        
        Args:
            flag: Flag to pass to uname (e.g., "-r", "-m")
        
        Returns:
            str: Output from uname command, or None
        """
        try:
            result = subprocess.run(
                ['uname', flag],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None

