"""
GLPI Agent Task Inventory MacOS Bios Module

This module collects BIOS/system information on macOS systems using 
system_profiler and ioreg.
"""

import subprocess
from typing import Dict, Any, Optional, List


class Bios:
    """MacOS Bios inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "bios"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the BIOS inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Get hardware information from system_profiler
        infos = self._get_system_profiler_infos(
            type='SPHardwareDataType',
            logger=logger
        )
        
        if not infos:
            if logger:
                logger.warning("Could not get system profiler information")
            return
        
        # Navigate to Hardware Overview
        info = infos.get('Hardware', {}).get('Hardware Overview', {})
        
        # Get platform expert device information
        devices = self._get_io_devices(
            io_class='IOPlatformExpertDevice',
            options='-r -l -w0 -d1',
            logger=logger
        )
        
        device = devices[0] if devices else {}
        
        # Set the BIOS information from the Apple system profiler
        bios_info = {
            'SMANUFACTURER': device.get('manufacturer') or 'Apple Inc',  # duh
            'SMODEL': (
                info.get('Model Identifier') or
                info.get('Machine Model') or
                device.get('model')
            ),
            # New method to get the SSN, because of MacOS 10.5.7 update
            # system_profiler gives 'Serial Number (system): XXXXX' where 10.5.6
            # and lower give 'Serial Number: XXXXX'
            'SSN': (
                info.get('Serial Number') or
                info.get('Serial Number (system)') or
                device.get('IOPlatformSerialNumber')
            ),
            'BVERSION': info.get('Boot ROM Version'),
        }
        
        # Filter out None values
        bios_info = {k: v for k, v in bios_info.items() if v is not None}
        
        inventory.set_bios(bios_info)
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        This function parses the text output of system_profiler and converts
        it into a nested dictionary structure.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query (e.g., 'SPHardwareDataType')
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
    
    def _get_io_devices(self, **params):
        """
        Get IO device information from ioreg command.
        
        Parses ioreg output to extract device information as a list of dictionaries.
        
        Args:
            **params: Keyword arguments including:
                - io_class: The IO class to query (e.g., 'IOPlatformExpertDevice')
                - options: Additional ioreg options
                - logger: Optional logger object
        
        Returns:
            list: List of device dictionaries
        """
        io_class = params.get('io_class', params.get('class'))
        options = params.get('options', '')
        logger = params.get('logger')
        
        # Build command
        command = ['ioreg']
        if io_class:
            command.extend(['-c', io_class])
        else:
            command.append('-l')
        
        # Add additional options
        if options:
            command.extend(options.split())
        
        # Get command output
        lines = self._get_all_lines(command=command, logger=logger)
        if not lines:
            return []
        
        devices = []
        device = None
        filter_class = io_class or r'[^,]+'
        
        for line in lines:
            # Check for start of device block
            if f'<class {filter_class},' in line or (not io_class and '<class ' in line):
                if device:
                    devices.append(device)
                # New device block
                device = {}
                continue
            
            if device is None:
                continue
            
            # Check for end of device block
            if '| }' in line:
                devices.append(device)
                device = None
                continue
            
            # Parse property lines: "key" = value or "key" = "value"
            if '=' in line:
                # Match patterns like: "manufacturer" = "Apple Inc"
                # or: "IOPlatformSerialNumber" = <serialnumber>
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip().strip('"')
                    value = parts[1].strip()
                    
                    # Remove angle brackets and quotes from value
                    if value.startswith('<') and value.endswith('>'):
                        value = value[1:-1]
                    elif value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    
                    device[key] = value
        
        # Include last device if it exists
        if device:
            devices.append(device)
        
        return devices
    
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
    
    def _can_run(self, command):
        """
        Check if a command can be run (exists and is executable).
        
        Args:
            command: Path to command to check
        
        Returns:
            bool: True if command exists and is executable
        """
        import os
        return os.path.isfile(command) and os.access(command, os.X_OK)

