"""
GLPI Agent Task Inventory MacOS Firewall Module

This module detects macOS firewall status using defaults and launchctl commands.
"""

import re
import subprocess
from typing import Dict, Any, Optional


class Firewall:
    """MacOS Firewall inventory module."""
    
    # Status constants
    STATUS_ON = "ON"
    STATUS_OFF = "OFF"
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "firewall"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if both 'defaults' and 'launchctl' commands are available.
        """
        return self._can_run('defaults') and self._can_run('launchctl')
    
    def do_inventory(self, **params):
        """
        Perform the firewall inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        firewall_status = self._get_firewall_status(logger=logger)
        
        inventory.add_entry(
            section='FIREWALL',
            entry={
                'STATUS': firewall_status
            }
        )
    
    def _get_firewall_status(self, **params):
        """
        Get the firewall status.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            str: STATUS_ON or STATUS_OFF
        """
        if not self._check_firewall_service(**params):
            return self.STATUS_OFF
        
        status = self._get_first_match(
            command='defaults read /Library/Preferences/com.apple.alf globalstate',
            pattern=r'^(\d)$',
            **params
        )
        
        if status and status == '1':
            return self.STATUS_ON
        else:
            return self.STATUS_OFF
    
    def _check_firewall_service(self, **params):
        """
        Check if the firewall service is running.
        
        Args:
            **params: Keyword arguments including:
                - pidFile: Optional file to read PID from
                - runningFile: Optional file to check running status
        
        Returns:
            bool: True if firewall service is running
        """
        pid = self._get_firewall_service_pid(
            file=params.get('pidFile')
        )
        
        if not pid:
            return False
        
        return self._check_running(
            pid=pid,
            file=params.get('runningFile')
        )
    
    def _get_firewall_service_pid(self, **params):
        """
        Get the PID of the firewall service.
        
        Args:
            **params: Keyword arguments including:
                - file: Optional file to read from
        
        Returns:
            str: PID of firewall service, or None
        """
        return self._get_first_match(
            command='launchctl list',
            pattern=r'^(\d+)\s+\S+\s+com\.apple\.alf$',
            **params
        )
    
    def _check_running(self, **params):
        """
        Check if a process with given PID is running.
        
        Args:
            **params: Keyword arguments including:
                - pid: Process ID to check
                - file: Optional file to read from
        
        Returns:
            bool: True if process is running
        """
        pid = params.get('pid')
        if not pid:
            return False
        
        result = self._get_first_match(
            command=f'sudo launchctl procinfo {pid}',
            pattern=r'^\s*state = running\s*$',
            **params
        )
        
        return bool(result)
    
    def _get_first_match(self, **params):
        """
        Execute a command and return the first regex match.
        
        Args:
            **params: Keyword arguments including:
                - command: Command to execute
                - pattern: Regex pattern to match
                - file: Optional file to read from
                - logger: Optional logger object
        
        Returns:
            str: First captured group from pattern match, or None
        """
        file_path = params.get('file')
        pattern = params.get('pattern')
        logger = params.get('logger')
        
        if not pattern:
            return None
        
        # Compile pattern if it's a string
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re.MULTILINE)
        
        # Get lines
        lines = self._get_all_lines(**params)
        
        for line in lines:
            match = pattern.match(line)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
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
                # Don't warn for expected failures (like when firewall is off)
                return []
            
            return result.stdout.splitlines()
        
        except subprocess.TimeoutExpired:
            if logger:
                logger.error(f"Command timed out: {' '.join(command)}")
            return []
        except FileNotFoundError:
            return []
        except Exception as e:
            if logger:
                logger.debug(f"Error executing command: {e}")
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

