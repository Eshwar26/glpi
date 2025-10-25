"""
GLPI Agent Task Inventory MacOS Networks Module

This module collects network interface information on macOS systems.
"""

import re
import subprocess
from typing import Dict, Any, Optional, List, Tuple


class Networks:
    """MacOS Networks inventory module."""
    
    # IP address pattern (simplified version)
    IP_ADDRESS_PATTERN = r'\d+\.\d+\.\d+\.\d+'
    HEX_IP_ADDRESS_PATTERN = r'[0-9a-f]{8}'
    MAC_ADDRESS_PATTERN = r'[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}'
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "network"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: True if ifconfig command is available.
        """
        return self._can_run('ifconfig')
    
    def do_inventory(self, **params):
        """
        Perform the network interface inventory and add results to inventory.
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        # Get routing table
        routes = self._get_routing_table(logger=logger)
        default = routes.get('0.0.0.0') or routes.get('default')
        
        # Get network interfaces
        interfaces = self._get_interfaces(logger=logger)
        
        for interface in interfaces:
            # If the default gateway address and the interface address belong to
            # the same network, that's the gateway for this network
            if default and interface.get('IPADDRESS') and interface.get('IPMASK'):
                if self._is_same_network(
                    default,
                    interface['IPADDRESS'],
                    interface['IPMASK']
                ):
                    interface['IPGATEWAY'] = default
            
            inventory.add_entry(
                section='NETWORKS',
                entry=interface
            )
        
        inventory.set_hardware({
            'DEFAULTGATEWAY': default
        })
    
    def _get_interfaces(self, **params):
        """
        Get network interface information.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            list: List of network interface dictionaries
        """
        logger = params.get('logger')
        
        netsetup = self._parse_network_setup(logger=logger, **params)
        
        interfaces = self._parse_ifconfig(
            command='/sbin/ifconfig -a',
            netsetup=netsetup,
            logger=logger
        )
        
        # Calculate subnet addresses
        for interface in interfaces:
            if interface.get('IPADDRESS') and interface.get('IPMASK'):
                interface['IPSUBNET'] = self._get_subnet_address(
                    interface['IPADDRESS'],
                    interface['IPMASK']
                )
        
        return interfaces
    
    def _parse_network_setup(self, **params):
        """
        Parse networksetup command output to get hardware port information.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
                - netsetup: Optional pre-parsed netsetup data (for testing)
        
        Returns:
            dict: Network setup information keyed by device name
        """
        # Can be provided by unittest
        if params.get('netsetup'):
            return params['netsetup']
        
        logger = params.get('logger')
        
        lines = self._get_all_lines(
            command='networksetup -listallhardwareports',
            logger=logger
        )
        
        if not lines:
            return {}
        
        netsetup = {}
        interface = None
        
        for line in lines:
            # Match "Hardware Port: Wi-Fi"
            match = re.match(r'^Hardware Port: (.+)$', line)
            if match:
                interface = {
                    'description': match.group(1)
                }
                continue
            
            # Match "Device: en0"
            match = re.match(r'^Device: (.+)$', line)
            if match:
                netsetup[match.group(1)] = interface
                continue
            
            # Match "Ethernet Address: 00:11:22:33:44:55"
            match = re.match(r'^Ethernet Address: (.+)$', line)
            if match and interface:
                interface['macaddr'] = match.group(1)
                continue
            
            # Stop at VLAN Configurations section
            if line.startswith('VLAN Configurations'):
                break
        
        return netsetup
    
    def _parse_ifconfig(self, **params):
        """
        Parse ifconfig command output.
        
        Args:
            **params: Keyword arguments including:
                - command: ifconfig command to execute
                - netsetup: Network setup information
                - logger: Optional logger object
        
        Returns:
            list: List of network interface dictionaries
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(**params)
        if not lines:
            return []
        
        netsetup = params.get('netsetup', {})
        interfaces = []
        interface = None
        
        for line in lines:
            # New interface line: "en0:"
            match = re.match(r'^(\S+):', line)
            if match:
                # Save previous interface
                if interface:
                    interfaces.append(interface)
                
                device_name = match.group(1)
                interface = {
                    'STATUS': 'Down',
                    'DESCRIPTION': (netsetup.get(device_name, {}).get('description') 
                                  if netsetup.get(device_name) 
                                  else device_name),
                    'VIRTUALDEV': 0 if netsetup.get(device_name) else 1
                }
                
                # Get MAC address from netsetup if available
                if netsetup.get(device_name) and netsetup[device_name].get('macaddr'):
                    interface['MACADDR'] = netsetup[device_name]['macaddr']
                
                # Set port type based on description
                if interface.get('DESCRIPTION'):
                    desc = interface['DESCRIPTION']
                    if re.match(r'^lo\d+$', desc):
                        interface['TYPE'] = 'loopback'
                    elif re.search(r'bridge', desc, re.IGNORECASE):
                        interface['TYPE'] = 'bridge'
                    elif re.search(r'wi-?fi', desc, re.IGNORECASE):
                        interface['TYPE'] = 'wifi'
                    elif re.search(r'bluetooth', desc, re.IGNORECASE):
                        interface['TYPE'] = 'bluetooth'
                    elif re.search(r'phone', desc, re.IGNORECASE):
                        interface['TYPE'] = 'dialup'
                    elif re.search(r'ethernet|thunderbolt|usb.*lan', desc, re.IGNORECASE):
                        interface['TYPE'] = 'ethernet'
                
                continue
            
            if not interface:
                continue
            
            # Parse inet address: "inet 192.168.1.100"
            match = re.search(rf'inet ({self.IP_ADDRESS_PATTERN})', line)
            if match:
                interface['IPADDRESS'] = match.group(1)
            
            # Parse inet6 address: "inet6 fe80::1"
            match = re.search(r'inet6 (\S+)', line)
            if match:
                ipv6 = match.group(1)
                # Drop the interface from the address (e.g., fe80::1%lo0 -> fe80::1)
                ipv6 = re.sub(r'%.*$', '', ipv6)
                interface['IPADDRESS6'] = ipv6
            
            # Parse netmask: "netmask 0xffffff00"
            match = re.search(rf'netmask 0x({self.HEX_IP_ADDRESS_PATTERN})', line)
            if match:
                interface['IPMASK'] = self._hex2canonical(match.group(1))
            
            # Parse MAC address: "ether 00:11:22:33:44:55"
            match = re.search(rf'(?:address:|ether|lladdr) ({self.MAC_ADDRESS_PATTERN})', line)
            if match:
                interface['MACADDR'] = match.group(1)
            
            # Parse MTU: "mtu 1500"
            match = re.search(r'mtu (\S+)', line)
            if match:
                interface['MTU'] = match.group(1)
            
            # Parse media type: "media autoselect"
            match = re.search(r'media (\S+)', line)
            if match and not interface.get('TYPE'):
                interface['TYPE'] = match.group(1)
            
            # Parse speed: "media: Ethernet 1000baseTX <full-duplex>"
            match = re.search(r'media: \S+ \((\d+)baseTX <.*>\)', line)
            if match:
                interface['SPEED'] = match.group(1)
            
            # Parse status: "status: active"
            if re.search(r'status:\s+active', line, re.IGNORECASE):
                interface['STATUS'] = 'Up'
            
            # If supported media is mentioned, it's not a virtual device
            if re.search(r'supported\smedia:', line):
                interface['VIRTUALDEV'] = 0
        
        # Add last interface
        if interface:
            interfaces.append(interface)
        
        return interfaces
    
    def _get_routing_table(self, **params):
        """
        Get the routing table.
        
        Args:
            **params: Keyword arguments including:
                - logger: Optional logger object
        
        Returns:
            dict: Routing table with destination IPs as keys
        """
        logger = params.get('logger')
        
        lines = self._get_all_lines(
            command='netstat -rn',
            logger=logger
        )
        
        if not lines:
            return {}
        
        routes = {}
        for line in lines:
            # Parse lines like: "default  192.168.1.1  UGSc  en0"
            # or: "0.0.0.0  192.168.1.1  UGSc  en0"
            parts = line.split()
            if len(parts) >= 2:
                destination = parts[0]
                gateway = parts[1]
                if destination in ('default', '0.0.0.0'):
                    routes[destination] = gateway
        
        return routes
    
    def _get_subnet_address(self, ip_address, netmask):
        """
        Calculate subnet address from IP address and netmask.
        
        Args:
            ip_address: IP address string (e.g., "192.168.1.100")
            netmask: Netmask string (e.g., "255.255.255.0")
        
        Returns:
            str: Subnet address (e.g., "192.168.1.0")
        """
        try:
            ip_parts = [int(x) for x in ip_address.split('.')]
            mask_parts = [int(x) for x in netmask.split('.')]
            
            subnet_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
            return '.'.join(str(x) for x in subnet_parts)
        except:
            return None
    
    def _is_same_network(self, ip1, ip2, netmask):
        """
        Check if two IP addresses are on the same network.
        
        Args:
            ip1: First IP address
            ip2: Second IP address
            netmask: Network mask
        
        Returns:
            bool: True if both IPs are on the same network
        """
        try:
            ip1_parts = [int(x) for x in ip1.split('.')]
            ip2_parts = [int(x) for x in ip2.split('.')]
            mask_parts = [int(x) for x in netmask.split('.')]
            
            network1 = [ip1_parts[i] & mask_parts[i] for i in range(4)]
            network2 = [ip2_parts[i] & mask_parts[i] for i in range(4)]
            
            return network1 == network2
        except:
            return False
    
    def _hex2canonical(self, hex_str):
        """
        Convert hexadecimal IP address to canonical dotted decimal notation.
        
        Args:
            hex_str: Hexadecimal IP address (e.g., "ffffff00")
        
        Returns:
            str: Canonical IP address (e.g., "255.255.255.0")
        """
        try:
            # Convert hex string to 4 bytes
            parts = []
            for i in range(0, 8, 2):
                parts.append(str(int(hex_str[i:i+2], 16)))
            return '.'.join(parts)
        except:
            return None
    
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

