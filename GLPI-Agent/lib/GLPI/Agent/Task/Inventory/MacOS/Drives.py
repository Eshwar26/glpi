"""
GLPI Agent Task Inventory MacOS Drives Module

This module collects drive/filesystem information on macOS systems using 
df, diskutil, and fdesetup commands.
"""

import re
import subprocess
from typing import Dict, Any, Optional, List


class Drives:
    """MacOS Drives inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "drive"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the drives/filesystem inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Get filesystem types
        all_types = self._get_filesystems_types_from_mount(logger=logger)
        
        # Filter out virtual/special filesystems
        excluded = {'fdesc', 'devfs', 'procfs', 'linprocfs', 'linsysfs', 'tmpfs', 'fdescfs'}
        types = [t for t in all_types if t not in excluded]
        
        # Get filesystems for each type
        filesystems_list = []
        for fs_type in types:
            fs_list = self._get_filesystems_from_df(
                logger=logger,
                command=f"df -P -k -t {fs_type}",
                fs_type=fs_type
            )
            filesystems_list.extend(fs_list)
        
        # Create dictionary keyed by volume name
        filesystems = {fs['VOLUMN']: fs for fs in filesystems_list if 'VOLUMN' in fs}
        
        # Get partition information
        partitions = self._get_partitions(logger=logger)
        
        for partition in partitions:
            device = f"/dev/{partition}"
            
            info = self._get_partition_info(
                command=f"diskutil info {partition}",
                logger=logger
            )
            
            filesystem = filesystems.get(device)
            if not filesystem:
                continue
            
            # Extract and set total size
            total_size = info.get('Total Size')
            if total_size:
                # Match pattern like "500.1 GB"
                match = re.match(r'^([\d.]+ \s+ \S+)', total_size, re.VERBOSE)
                if match:
                    filesystem['TOTAL'] = self._get_canonical_size(match.group(1))
            
            # Set additional filesystem properties
            filesystem['SERIAL'] = info.get('Volume UUID') or info.get('UUID')
            filesystem['FILESYSTEM'] = info.get('File System') or info.get('Partition Type')
            filesystem['LABEL'] = info.get('Volume Name')
        
        # Check FileVault 2 support for root filesystem
        if self._can_run('fdesetup'):
            status = self._get_first_line(command='fdesetup status', logger=logger)
            if status and re.search(r'FileVault is On', status, re.IGNORECASE):
                if logger:
                    logger.debug("FileVault 2 is enabled")
                
                # Find root filesystem
                rootfs = None
                for fs in filesystems.values():
                    if fs.get('TYPE') == '/':
                        rootfs = fs
                        break
                
                if rootfs:
                    rootfs['ENCRYPT_STATUS'] = 'Yes'
                    rootfs['ENCRYPT_NAME'] = 'FileVault 2'
                    rootfs['ENCRYPT_ALGO'] = 'XTS_AES_128'
            else:
                if logger:
                    logger.debug("FileVault 2 is disabled")
        else:
            if logger:
                logger.debug("FileVault 2 is not supported")
        
        # Add filesystems to the inventory
        for key in sorted(filesystems.keys()):
            inventory.add_entry(
                section='DRIVES',
                entry=filesystems[key]
            )
    
    def _get_partitions(self, **params):
        """
        Get list of disk partitions from diskutil.
        
        Args:
            **params: Keyword arguments including:
                - command: Command to execute (default: "diskutil list")
                - logger: Optional logger object
        
        Returns:
            list: List of partition identifiers (e.g., ["disk0s1", "disk0s2"])
        """
        command = params.get('command', 'diskutil list')
        logger = params.get('logger')
        
        lines = self._get_all_lines(command=command, logger=logger)
        if not lines:
            return []
        
        devices = []
        for line in lines:
            # Partition identifiers look like disk0s1
            match = re.search(r'(disk\d+s\d+)$', line, re.VERBOSE)
            if match:
                devices.append(match.group(1))
        
        return devices
    
    def _get_partition_info(self, **params):
        """
        Get detailed information about a partition from diskutil info.
        
        Args:
            **params: Keyword arguments including:
                - command: Command to execute (e.g., "diskutil info disk0s1")
                - logger: Optional logger object
        
        Returns:
            dict: Partition information as key-value pairs
        """
        command = params.get('command')
        logger = params.get('logger')
        
        lines = self._get_all_lines(command=command, logger=logger)
        if not lines:
            return {}
        
        info = {}
        for line in lines:
            # Match lines like "   Total Size:              500.1 GB"
            match = re.match(r'(\S[^:]+)\s*:\s+(\S.*\S)', line, re.VERBOSE)
            if match:
                info[match.group(1)] = match.group(2)
        
        return info
    
    def _get_filesystems_types_from_mount(self, **params):
        """
        Get list of filesystem types from mount command.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of unique filesystem types
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(command='mount', logger=logger)
        if not lines:
            return []
        
        types = set()
        for line in lines:
            # Mount lines look like: "/dev/disk1s1 on / (apfs, local, journaled)"
            # Extract filesystem type from parentheses
            match = re.search(r'\(([^,\s]+)', line)
            if match:
                types.add(match.group(1))
        
        return list(types)
    
    def _get_filesystems_from_df(self, **params):
        """
        Get filesystem information from df command.
        
        Args:
            **params: Keyword arguments including:
                - command: df command to execute
                - fs_type: Filesystem type
                - logger: Optional logger object
        
        Returns:
            list: List of filesystem dictionaries
        """
        command = params.get('command')
        fs_type = params.get('fs_type', params.get('type'))
        logger = params.get('logger')
        
        lines = self._get_all_lines(command=command, logger=logger)
        if not lines:
            return []
        
        filesystems = []
        
        # Skip header line
        for line in lines[1:]:
            # df -P output format:
            # Filesystem   1024-blocks      Used Available Capacity Mounted on
            parts = line.split()
            if len(parts) < 6:
                continue
            
            filesystem = {
                'VOLUMN': parts[0],  # Device name (e.g., /dev/disk1s1)
                'TOTAL': parts[1],   # Total size in KB
                'FREE': parts[3],    # Available space in KB
                'TYPE': parts[5],    # Mount point
                'FILESYSTEM': fs_type,
            }
            
            filesystems.append(filesystem)
        
        return filesystems
    
    def _get_canonical_size(self, size_str):
        """
        Convert size string to MB.
        
        Args:
            size_str: Size string like "500.1 GB" or "256 MB"
        
        Returns:
            int: Size in MB
        """
        if not size_str:
            return None
        
        # Match number and unit
        match = re.match(r'([\d.]+)\s*([KMGTP]?B?)', size_str, re.IGNORECASE)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to MB
        if unit in ('B', 'BYTES'):
            value = value / (1024 * 1024)
        elif unit in ('K', 'KB', 'KIB'):
            value = value / 1024
        elif unit in ('M', 'MB', 'MIB'):
            pass  # Already in MB
        elif unit in ('G', 'GB', 'GIB'):
            value = value * 1024
        elif unit in ('T', 'TB', 'TIB'):
            value = value * 1024 * 1024
        elif unit in ('P', 'PB', 'PIB'):
            value = value * 1024 * 1024 * 1024
        
        return int(value)
    
    def _get_first_line(self, **params):
        """
        Execute a command and return the first line of output.
        
        Args:
            **params: Keyword arguments including:
                - command: Command to execute
                - logger: Optional logger object
        
        Returns:
            str: First line of output, or None if no output
        """
        lines = self._get_all_lines(**params)
        return lines[0] if lines else None
    
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
        Check if a command can be run (exists in PATH or is executable file).
        
        Args:
            command: Command name or path to check
        
        Returns:
            bool: True if command can be run
        """
        import os
        import shutil
        
        # Check if it's an absolute path
        if os.path.isabs(command):
            return os.path.isfile(command) and os.access(command, os.X_OK)
        
        # Check if command exists in PATH
        return shutil.which(command) is not None

