"""
GLPI Agent Task Inventory MacOS OS Module

This module collects operating system information on macOS systems.
"""

import os
import re
import time
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime


class OS:
    """MacOS OS inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "os"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the OS inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        kernel_release = self._uname("-r")
        kernel_arch = self._uname("-m")
        
        boottime = self._get_boot_time()
        
        os_info = {
            'NAME': 'MacOSX',
            'KERNEL_VERSION': kernel_release,
            'ARCH': kernel_arch,
            'BOOT_TIME': self._get_formatted_local_time(boottime) if boottime else None
        }
        
        # Get system version information
        infos = self._get_system_profiler_infos(
            logger=logger,
            type='SPSoftwareDataType'
        )
        
        system_version = (infos.get('Software', {})
                         .get('System Software Overview', {})
                         .get('System Version'))
        
        if system_version:
            # Extract name and version from string like "macOS 11.6"
            match = re.match(r'^(.*?)\s+(\d+.*)', system_version)
            if match:
                os_info['FULL_NAME'] = match.group(1)
                os_info['VERSION'] = match.group(2)
        
        # Get install date from .AppleSetupDone file
        if os.path.isfile("/var/db/.AppleSetupDone"):
            install_date = self._get_install_date(
                command="stat -f %m /var/db/.AppleSetupDone",
                logger=logger
            )
            if install_date:
                os_info['INSTALL_DATE'] = install_date
        
        # Filter out None values
        os_info = {k: v for k, v in os_info.items() if v is not None}
        
        inventory.set_operating_system(os_info)
    
    def _get_install_date(self, **params):
        """
        Get the OS install date.
        
        Args:
            **params: Keyword arguments including:
                - command: Command to execute
                - logger: Optional logger object
        
        Returns:
            str: Formatted install date
        """
        date_str = self._get_first_line(**params)
        if not date_str:
            return None
        
        try:
            # Try to parse as epoch timestamp
            timestamp = int(date_str)
            
            # Try to use datetime if available
            try:
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return self._get_formatted_local_time(timestamp)
        except ValueError:
            return None
    
    def _get_boot_time(self):
        """
        Get the system boot time.
        
        Returns:
            int: Boot time as Unix timestamp, or None
        """
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
        except:
            pass
        
        return None
    
    def _get_formatted_local_time(self, timestamp):
        """
        Format a Unix timestamp as local time string.
        
        Args:
            timestamp: Unix timestamp (seconds since epoch)
        
        Returns:
            str: Formatted time string
        """
        if not timestamp:
            return None
        
        try:
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
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
    
    def _get_first_line(self, **params):
        """
        Execute a command and return the first line of output.
        
        Args:
            **params: Keyword arguments including:
                - command: Command to execute
                - logger: Optional logger object
        
        Returns:
            str: First line of output, or None
        """
        lines = self._get_all_lines(**params)
        return lines[0] if lines else None
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query
                - logger: Optional logger object
        
        Returns:
            dict: Parsed system profiler information as nested dictionary
        """
        profiler_type = params.get('type', '')
        logger = params.get('logger')
        
        # Build command
        command = ['/usr/sbin/system_profiler']
        if profiler_type:
            command.append(profiler_type)
        
        # Get command output
        lines = self._get_all_lines(command=command, logger=logger)
        if not lines:
            return {}
        
        # Parse the output into a nested dictionary
        info = {}
        parents = [(info, -1, None)]
        
        for line in lines:
            # Match lines in format: "    Key: Value" or "    Key:"
            if ':' not in line:
                continue
            
            # Calculate indentation level
            stripped = line.lstrip()
            level = len(line) - len(stripped)
            
            # Split into key and value
            parts = line.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            
            # Get current parent
            parent_node, parent_level, _ = parents[-1]
            
            if value:
                # Check indentation level against parent node
                if level <= parent_level:
                    # Check if parent node is empty and needs cleanup
                    if len(parent_node) == 0 and len(parents) > 1:
                        parent_key = parents[-1][2]
                        if parent_key:
                            parents[-2][0][parent_key] = None
                    
                    # Unstack nodes until suitable parent is found
                    while len(parents) > 1 and level <= parents[-1][1]:
                        parents.pop()
                    parent_node = parents[-1][0]
                
                # Add the value to current node
                parent_node[key] = value
            else:
                # No value means this is a new section
                # Compare level with parent
                if level < parent_level:
                    # Up the tree: unstack until suitable parent found
                    while len(parents) > 1 and level <= parents[-1][1]:
                        parents.pop()
                elif level == parent_level:
                    # Same level: unstack last node
                    if len(parents) > 1:
                        parents.pop()
                # else: level > parent_level, down the tree, no change
                
                # Create new node and push to stack
                parent_node = parents[-1][0]
                
                # Handle duplicate keys
                original_key = key
                counter = 1
                while key in parent_node:
                    key = f"{original_key}_{counter}"
                    counter += 1
                
                parent_node[key] = {}
                parents.append((parent_node[key], level, key))
        
        return info
    
    def _get_all_lines(self, **params):
        """
        Execute a command and return all output lines.
        
        Args:
            **params: Keyword arguments including:
                - command: List or string command to execute
                - logger: Optional logger object
        
        Returns:
            list: List of output lines from the command
        """
        command = params.get('command')
        logger = params.get('logger')
        
        if not command:
            return []
        
        # Ensure command is a list
        if isinstance(command, str):
            command = command.split()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                if logger:
                    logger.warning(
                        f"Command failed with return code {result.returncode}: {' '.join(command)}"
                    )
                return []
            
            return result.stdout.splitlines()
        
        except subprocess.TimeoutExpired:
            if logger:
                logger.error(f"Command timed out: {' '.join(command)}")
            return []
        except FileNotFoundError:
            if logger:
                logger.error(f"Command not found: {command[0]}")
            return []
        except Exception as e:
            if logger:
                logger.error(f"Error executing command: {e}")
            return []

