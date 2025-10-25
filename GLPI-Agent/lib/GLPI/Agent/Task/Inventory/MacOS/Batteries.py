"""
GLPI Agent Task Inventory MacOS Batteries Module

This module collects battery information on macOS systems using system_profiler.
"""

import subprocess
from typing import Dict, Any, Optional


class Batteries:
    """MacOS Batteries inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "battery"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the battery inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        battery = self._get_battery(logger=logger, format='xml')
        if not battery:
            return
        
        inventory.add_entry(
            section='BATTERIES',
            entry=battery
        )
    
    def _get_battery(self, **params):
        """
        Get battery information from system_profiler.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object for logging
                - format: Format parameter (currently unused, kept for compatibility)
        
        Returns:
            dict: Battery information dictionary with keys:
                - SERIAL: Battery serial number
                - CAPACITY: Full charge capacity in mAh
                - NAME: Device name
                - MANUFACTURER: Battery manufacturer
                - VOLTAGE: Voltage in mV
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            type='SPPowerDataType',
            format='text',
            logger=logger
        )
        
        if not infos:
            return None
        
        # Navigate through the nested dictionary structure
        power_info = infos.get('Power', {})
        info_battery = power_info.get('Battery Information', {})
        
        if not info_battery:
            return None
        
        model_info = info_battery.get('Model Information', {})
        charge_info = info_battery.get('Charge Information', {})
        
        battery = {
            'SERIAL': model_info.get('Serial Number'),
            'CAPACITY': charge_info.get('Full Charge Capacity (mAh)'),
            'NAME': model_info.get('Device Name'),
            'MANUFACTURER': model_info.get('Manufacturer'),
            'VOLTAGE': info_battery.get('Voltage (mV)'),
            # CHEMISTRY and DATE fields are commented out in original
            # as they may not be consistently available
        }
        
        # Filter out None values
        battery = {k: v for k, v in battery.items() if v is not None}
        
        return battery if battery else None
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        This function parses the text output of system_profiler and converts
        it into a nested dictionary structure.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query (e.g., 'SPPowerDataType')
                - format: Output format ('text' or 'xml')
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

