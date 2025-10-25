"""
GLPI Agent Task Inventory MacOS CPU Module

This module collects CPU information on macOS systems using 
system_profiler and sysctl.
"""

import re
import subprocess
from typing import Dict, Any, Optional, List


class CPU:
    """MacOS CPU inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "cpu"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if /usr/sbin/system_profiler command is available.
        """
        return self._can_run('/usr/sbin/system_profiler')
    
    def do_inventory(self, **params):
        """
        Perform the CPU inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        cpus = self._get_cpus(logger=logger)
        
        for cpu in cpus:
            inventory.add_entry(
                section='CPUS',
                entry=cpu
            )
    
    def _get_cpus(self, **params):
        """
        Get CPU information from system_profiler and sysctl.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object for logging
                - file: Optional file to read system_profiler output from
                - sysctl: Optional file to read sysctl output from
        
        Returns:
            list: List of CPU information dictionaries
        """
        logger = params.get('logger')
        
        # Get system profiler information
        infos = self._get_system_profiler_infos(
            type='SPHardwareDataType',
            logger=logger,
            file=params.get('file')
        )
        
        if not infos:
            return []
        
        sysprofile_info = infos.get('Hardware', {}).get('Hardware Overview', {})
        
        # Get more information from sysctl
        lines = self._get_all_lines(
            logger=logger,
            command='sysctl -a machdep.cpu',
            file=params.get('sysctl')
        )
        
        if not lines:
            return []
        
        sysctl_info = {}
        for line in lines:
            # Match pattern: "key : value"
            match = re.match(r'([^:]+)\s*:\s*(.+)', line)
            if match:
                sysctl_info[match.group(1)] = match.group(2)
        
        # Get CPU type/name
        cpu_type = (
            sysctl_info.get('machdep.cpu.brand_string') or
            sysprofile_info.get('Processor Name') or
            sysprofile_info.get('CPU Type')
        )
        
        # Get number of processors
        procs = (
            sysprofile_info.get('Number Of Processors') or
            sysprofile_info.get('Number Of CPUs') or
            1
        )
        try:
            procs = int(procs)
        except (ValueError, TypeError):
            procs = 1
        
        # Get processor speed
        speed = (
            sysprofile_info.get('Processor Speed') or
            sysprofile_info.get('CPU Speed') or
            ""
        )
        
        # Get additional CPU details
        stepping = sysctl_info.get('machdep.cpu.stepping')
        family = sysctl_info.get('machdep.cpu.family')
        model = sysctl_info.get('machdep.cpu.model')
        threads = sysctl_info.get('machdep.cpu.thread_count')
        
        # Process speed
        # French Mac returns 2,60 Ghz instead of 2.60 Ghz :D
        if speed:
            speed = speed.replace(',', '.')
            
            if re.search(r'GHz$', speed, re.IGNORECASE):
                speed = re.sub(r'GHz', '', speed, flags=re.IGNORECASE)
                try:
                    speed = float(speed) * 1000
                except ValueError:
                    speed = None
            elif re.search(r'MHz$', speed, re.IGNORECASE):
                speed = re.sub(r'MHz', '', speed, flags=re.IGNORECASE)
                try:
                    speed = float(speed)
                except ValueError:
                    speed = None
            
            if speed:
                # Remove whitespace
                speed = str(speed).replace(' ', '')
        
        # Calculate cores
        total_cores = sysprofile_info.get('Total Number Of Cores')
        if total_cores:
            try:
                cores = int(total_cores) / procs
            except (ValueError, TypeError, ZeroDivisionError):
                cores = sysctl_info.get('machdep.cpu.core_count')
        else:
            cores = sysctl_info.get('machdep.cpu.core_count')
        
        # Convert cores to int if possible
        if cores:
            try:
                cores = int(cores)
            except (ValueError, TypeError):
                pass
        
        # Determine manufacturer from CPU type
        manufacturer = None
        if cpu_type:
            if re.search(r'Intel', cpu_type, re.IGNORECASE):
                manufacturer = "Intel"
            elif re.search(r'AMD', cpu_type, re.IGNORECASE):
                manufacturer = "AMD"
            elif re.search(r'Apple', cpu_type, re.IGNORECASE):
                manufacturer = "Apple"
        
        # Build CPU info dictionary
        cpu = {
            'CORE': cores,
            'MANUFACTURER': manufacturer,
            'NAME': self._trim_whitespace(cpu_type) if cpu_type else None,
            'THREAD': threads,
        }
        
        # Add Intel/AMD specific fields
        if family is not None:
            cpu['FAMILYNUMBER'] = family
        if model is not None:
            cpu['MODEL'] = model
        if stepping is not None:
            cpu['STEPPING'] = stepping
        if speed:
            cpu['SPEED'] = speed
        
        # Filter out None values
        cpu = {k: v for k, v in cpu.items() if v is not None}
        
        # Create list with one entry per processor
        cpus = []
        for i in range(procs):
            cpus.append(cpu.copy())
        
        return cpus
    
    def _get_system_profiler_infos(self, **params):
        """
        Get structured information from system_profiler command.
        
        Args:
            **params: Keyword arguments including:
                - type: The data type to query (e.g., 'SPHardwareDataType')
                - logger: Optional logger object
                - file: Optional file to read from instead of running command
        
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
                - logger: Optional logger object
                - file: Optional file path to read from instead of running command
        
        Returns:
            list: List of output lines from the command or file
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
    
    def _trim_whitespace(self, text):
        """
        Trim leading and trailing whitespace and normalize internal whitespace.
        
        Args:
            text: String to trim
        
        Returns:
            str: Trimmed string
        """
        if not text:
            return text
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
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

