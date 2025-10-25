"""
GLPI Agent Task Inventory MacOS USB Module

This module collects USB device information on macOS systems.
"""

import subprocess
from typing import Dict, Any, Optional, List


class USB:
    """MacOS USB inventory module."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "usb"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the USB device inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        seen = set()
        
        devices = self._get_devices(logger=logger)
        for device in devices:
            # Avoid duplicates based on serial number
            serial = device.get('SERIAL')
            if serial and serial in seen:
                continue
            if serial:
                seen.add(serial)
            
            inventory.add_entry(
                section='USBDEVICES',
                entry=device
            )
    
    def _get_devices(self, **params):
        """
        Get USB device information.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of USB device dictionaries
        """
        logger = params.get('logger')
        
        io_devices = self._get_io_devices(
            io_class='IOUSBDevice',
            options='-r -l -w0 -d1',
            logger=logger
        )
        
        devices = []
        for dev in io_devices:
            device = {
                'VENDORID': self._dec2hex(dev.get('idVendor')),
                'PRODUCTID': self._dec2hex(dev.get('idProduct')),
                'SERIAL': dev.get('USB Serial Number'),
                'NAME': dev.get('USB Product Name'),
                'CLASS': dev.get('bDeviceClass'),
                'SUBCLASS': dev.get('bDeviceSubClass')
            }
            
            # Filter out None values
            device = {k: v for k, v in device.items() if v is not None}
            
            if device:
                devices.append(device)
        
        return devices
    
    def _dec2hex(self, value):
        """
        Convert decimal value to hexadecimal string.
        
        Args:
            value: Decimal value (string or int)
        
        Returns:
            str: Hexadecimal string (e.g., "05ac"), or None
        """
        if not value:
            return None
        
        try:
            # Convert to int if it's a string
            if isinstance(value, str):
                value = int(value)
            
            # Convert to hex and remove '0x' prefix
            return format(value, '04x')
        except (ValueError, TypeError):
            return None
    
    def _get_io_devices(self, **params):
        """
        Get IO device information from ioreg command.
        
        Args:
            **params: Keyword arguments including:
                - io_class: The IO class to query
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
        
        for line in lines:
            # Check for start of device block
            if '<class ' in line:
                if device:
                    devices.append(device)
                device = {}
                continue
            
            if device is None:
                continue
            
            # Check for end of device block
            if '| }' in line:
                devices.append(device)
                device = None
                continue
            
            # Parse property lines
            if '=' in line:
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

