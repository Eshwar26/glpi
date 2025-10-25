"""
GLPI Agent Task Inventory MacOS Memory Module

This module collects memory/RAM information on macOS systems.
"""

import re
import subprocess
from typing import Dict, Any, Optional, List


class Memory:
    """MacOS Memory inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "memory"
    
    @staticmethod
    def run_me_if_these_checks_failed():
        """
        Return list of modules to run if these checks failed.
        
        Returns:
            list: List of module names
        """
        return ["GLPI::Agent::Task::Inventory::Generic::Dmidecode"]
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the memory inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Get individual memory modules
        memories = self._get_memories(logger=logger)
        for memory in memories:
            inventory.add_entry(
                section='MEMORIES',
                entry=memory
            )
        
        # Get total memory
        total_memory = self._get_memory(logger=logger)
        inventory.set_hardware({
            'MEMORY': total_memory,
        })
    
    def _get_memories(self, **params):
        """
        Get individual memory module information.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
                - file: Optional file to read from
        
        Returns:
            list: List of memory module dictionaries
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            type='SPMemoryDataType',
            logger=logger,
            file=params.get('file')
        )
        
        if not infos.get('Memory'):
            return []
        
        # The memory slot information may appear directly under
        # 'Memory' top-level node, or under Memory/Memory Slots
        parent_node = (infos['Memory'].get('Memory Slots') 
                      if infos['Memory'].get('Memory Slots') 
                      else infos['Memory'])
        
        memories = []
        for key in sorted(parent_node.keys()):
            # Match DIMM slots like "DIMM0", "DIMM1", etc.
            match = re.match(r'DIMM(\d+)', key)
            if not match:
                continue
            
            slot = match.group(1)
            info = parent_node[key]
            
            description = info.get('Part Number')
            
            # Convert hexa to ASCII
            if description and description.startswith('0x'):
                try:
                    hex_str = description[2:]
                    description = bytes.fromhex(hex_str).decode('ascii')
                    description = description.rstrip()
                except:
                    pass
            
            description = self._get_sanitized_string(description)
            
            memory = {
                'NUMSLOTS': slot,
                'CAPTION': f"Status: {info.get('Status', '')}",
                'TYPE': info.get('Type'),
                'SERIALNUMBER': info.get('Serial Number'),
                'SPEED': self._get_canonical_speed(info.get('Speed')),
                'CAPACITY': self._get_canonical_size(info.get('Size'), 1024)
            }
            
            if description:
                memory['DESCRIPTION'] = description
            
            # Filter out None values
            memory = {k: v for k, v in memory.items() if v is not None}
            
            memories.append(memory)
        
        # Apple M1 support (integrated memory)
        if not memories and parent_node.get('Memory') and parent_node.get('Type'):
            memories.append({
                'NUMSLOTS': 0,
                'DESCRIPTION': 'Integrated memory',
                'TYPE': parent_node.get('Type'),
                'CAPACITY': self._get_canonical_size(parent_node.get('Memory'), 1024)
            })
        
        return memories
    
    def _get_memory(self, **params):
        """
        Get total system memory.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
                - file: Optional file to read from
        
        Returns:
            int: Total memory in MB, or None
        """
        logger = params.get('logger')
        
        infos = self._get_system_profiler_infos(
            type='SPMemoryDataType',
            logger=logger,
            file=params.get('file')
        )
        
        memory_str = (infos.get('Hardware', {})
                     .get('Hardware Overview', {})
                     .get('Memory'))
        
        return self._get_canonical_size(memory_str, 1024)
    
    def _get_canonical_size(self, size_str, base=1024):
        """
        Convert size string to MB.
        
        Args:
            size_str: Size string like "16 GB" or "8192 MB"
            base: Base for conversion (1024 or 1000)
        
        Returns:
            int: Size in MB, or None
        """
        if not size_str:
            return None
        
        # Match number and unit
        match = re.match(r'([\d.]+)\s*([KMGTP]?B?)', str(size_str), re.IGNORECASE)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to MB
        if unit in ('B', 'BYTES'):
            value = value / (base * base)
        elif unit in ('K', 'KB', 'KIB'):
            value = value / base
        elif unit in ('M', 'MB', 'MIB'):
            pass  # Already in MB
        elif unit in ('G', 'GB', 'GIB'):
            value = value * base
        elif unit in ('T', 'TB', 'TIB'):
            value = value * base * base
        elif unit in ('P', 'PB', 'PIB'):
            value = value * base * base * base
        
        return int(value)
    
    def _get_canonical_speed(self, speed_str):
        """
        Convert speed string to MHz.
        
        Args:
            speed_str: Speed string like "2400 MHz" or "2.4 GHz"
        
        Returns:
            str: Speed in MHz, or None
        """
        if not speed_str:
            return None
        
        # Match number and unit
        match = re.match(r'([\d.]+)\s*([MG]?Hz)', str(speed_str), re.IGNORECASE)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to MHz
        if unit == 'GHZ':
            value = value * 1000
        elif unit == 'MHZ':
            pass  # Already in MHz
        
        return str(int(value))
    
    def _get_sanitized_string(self, text):
        """
        Sanitize a string by removing control characters.
        
        Args:
            text: String to sanitize
        
        Returns:
            str: Sanitized string, or None
        """
        if not text:
            return None
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        text = text.strip()
        
        return text if text else None
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query
                - logger: Optional logger object
                - file: Optional file to read from
        
        Returns:
            dict: Parsed system profiler information as nested dictionary
        """
        profiler_type = params.get('type', '')
        logger = params.get('logger')
        file_path = params.get('file')
        
        # Build command
        command = ['/usr/sbin/system_profiler']
        if profiler_type:
            command.append(profiler_type)
        
        # Get command output
        lines = self._get_all_lines(command=command, logger=logger, file=file_path)
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
        Execute a command and return all output lines, or read from file.
        
        Args:
            **params: Keyword arguments including:
                - command: List or string command to execute
                - file: Optional file path to read from
                - logger: Optional logger object
        
        Returns:
            list: List of output lines
        """
        file_path = params.get('file')
        logger = params.get('logger')
        
        # If file is specified, read from it
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read().splitlines()
            except Exception as e:
                if logger:
                    logger.error(f"Error reading file {file_path}: {e}")
                return []
        
        command = params.get('command')
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

