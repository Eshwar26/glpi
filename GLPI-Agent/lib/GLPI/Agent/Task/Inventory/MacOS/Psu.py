"""
GLPI Agent Task Inventory MacOS PSU Module

This module collects power supply/charger information on macOS systems.
"""

import subprocess
from typing import Dict, Any, Optional, List


class Psu:
    """MacOS PSU inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "psu"
    
    @staticmethod
    def run_after_if_enabled():
        """
        Return list of modules to run after if enabled.
        
        Returns:
            list: List of module names
        """
        return ["GLPI::Agent::Task::Inventory::Generic::Dmidecode::Psu"]
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the PSU/charger inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        charger = self._get_charger(logger=logger)
        if not charger:
            return
        
        # Get existing power supplies from inventory
        section = inventory.get_section('POWERSUPPLIES') or []
        psulist = []
        
        # Collect existing power supplies
        for psu in section:
            psulist.append(psu)
        
        # Merge charger info (simple approach - just add it)
        # In a full implementation, this would use a PowerSupplies manager
        # to merge based on serial numbers and other identifying info
        psulist.append(charger)
        
        # Clear section and add back merged power supplies
        inventory.clear_section('POWERSUPPLIES')
        for psu in psulist:
            inventory.add_entry(
                section='POWERSUPPLIES',
                entry=psu
            )
    
    def _get_charger(self, **params):
        """
        Get AC charger information.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            dict: Charger information dictionary, or None
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            type='SPPowerDataType',
            format='text',
            logger=logger
        )
        
        if not infos.get('Power'):
            return None
        
        info_power = infos['Power'].get('AC Charger Information')
        if not info_power:
            return None
        
        charger = {
            'SERIALNUMBER': info_power.get('Serial Number'),
            'NAME': info_power.get('Name'),
            'MANUFACTURER': info_power.get('Manufacturer'),
            'STATUS': ('Charging' 
                      if info_power.get('Charging') == 'Yes' 
                      else 'Not charging'),
            'PLUGGED': info_power.get('Connected', 'No'),
            'POWER_MAX': info_power.get('Wattage (W)'),
        }
        
        # Filter out None values
        charger = {k: v for k, v in charger.items() if v is not None}
        
        return charger if charger else None
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query
                - format: Format parameter (kept for compatibility)
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

