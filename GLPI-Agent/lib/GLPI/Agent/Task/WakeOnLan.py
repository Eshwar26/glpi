"""
GLPI Agent Task WakeOnLan Module

This task sends a wake-on-lan packet to another host on the same network as the
agent host.
"""

import os
import re
import socket
import struct
import platform
from typing import List, Dict, Optional

from GLPI.Agent.Task.WakeOnLan.Version import VERSION

__version__ = VERSION

# MAC address pattern for validation
MAC_ADDRESS_PATTERN = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'


class WakeOnLanTask:
    """GLPI Agent Wake-on-LAN Task"""
    
    def __init__(self, logger=None, config=None, target=None, deviceid=None):
        """Initialize the WakeOnLan task"""
        self.logger = logger
        self.config = config
        self.target = target
        self.deviceid = deviceid
        self.addresses = []
    
    def is_enabled(self, contact=None) -> bool:
        """Check if the task is enabled"""
        if not self.target or not self.target.is_type('server'):
            if self.logger:
                self.logger.debug("WakeOnLan task not compatible with local target")
            return False
        
        # TODO Support WakeOnLan task via GLPI Agent Protocol
        if contact and type(contact).__module__.startswith('GLPI.Agent.Protocol'):
            return False
        
        if not contact:
            return False
        
        options = contact.get_options_info_by_name('WAKEONLAN')
        if not options:
            if self.logger:
                self.logger.debug("WakeOnLan task execution not requested")
            return False
        
        addresses = []
        for option in options:
            for param in option.get('PARAM', []):
                address = param.get('MAC')
                if not address:
                    continue
                
                if not re.match(MAC_ADDRESS_PATTERN, address):
                    if self.logger:
                        self.logger.error(f"invalid MAC address {address}, skipping")
                    continue
                
                # Remove colons from MAC address
                address = address.replace(':', '').replace('-', '')
                addresses.append(address)
        
        if not addresses:
            if self.logger:
                self.logger.error("no mac address defined")
            return False
        
        self.addresses = addresses
        return True
    
    def run(self, methods: Optional[List[str]] = None) -> None:
        """Run the WakeOnLan task"""
        # Just reset event if run as an event to not trigger another one
        if hasattr(self, 'reset_event'):
            self.reset_event()
        
        if methods is None:
            methods = ['ethernet', 'udp']
        
        for method in methods:
            method_name = f'_send_magic_packet_{method}'
            
            if not hasattr(self, method_name):
                continue
            
            for address in self.addresses:
                try:
                    getattr(self, method_name)(address)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Impossible to use {method} method: {e}")
                    # This method doesn't work, skip remaining addresses
                    break
            
            # All addresses have been processed, skip other methods
            break
    
    def _send_magic_packet_ethernet(self, target: str) -> None:
        """
        Send magic packet via Ethernet frame.
        Requires root privileges.
        """
        # Check for root privileges
        if os.geteuid() != 0:
            raise PermissionError("root privileges needed")
        
        # Try to import Net::Write equivalent (would need a Python library)
        # For now, this is a placeholder
        try:
            # Would need a library like scapy for raw ethernet frames
            # from scapy.all import sendp, Ether
            pass
        except ImportError:
            raise ImportError("Raw ethernet packet library needed (e.g., scapy)")
        
        interfaces = self._get_interfaces()
        
        for interface in interfaces:
            source = interface.get('MACADDR', '')
            source = source.replace(':', '')
            dev = interface.get('DESCRIPTION', '')
            
            # Build packet
            payload = self._get_payload(target)
            # packet = target_mac + source_mac + ethertype + payload
            # In a real implementation, would use scapy or similar
            
            if self.logger:
                self.logger.debug(
                    f"Sending magic packet to {target} as ethernet frame on {dev}"
                )
            
            # Placeholder for actual sending
            # sendp(Ether(dst=target, src=source, type=0x0842)/payload, iface=dev)
    
    def _send_magic_packet_udp(self, target: str) -> None:
        """Send magic packet via UDP broadcast"""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            packet = self._get_payload(target)
            destination = ('255.255.255.255', 9)
            
            if self.logger:
                self.logger.debug(f"Sending magic packet to {target} as UDP packet")
            
            sock.sendto(packet, destination)
            sock.close()
            
        except Exception as e:
            raise Exception(f"can't send packet: {e}")
    
    def _get_interfaces(self) -> List[Dict[str, str]]:
        """Get network interfaces for the system"""
        interfaces = []
        system = platform.system()
        
        if system == 'Linux':
            # Would import from GLPI.Agent.Tools.Linux
            # interfaces = get_interfaces_from_ifconfig(logger=self.logger)
            pass
        
        elif system in ['FreeBSD', 'OpenBSD', 'NetBSD', 'DragonFly']:
            # Would import from GLPI.Agent.Tools.BSD
            # interfaces = get_interfaces_from_ifconfig(logger=self.logger)
            pass
        
        elif system == 'Windows':
            # Would import from GLPI.Agent.Tools.Win32
            # interfaces = get_interfaces(logger=self.logger)
            # On Windows, we have to use internal device name instead of literal name
            for interface in interfaces:
                if 'PNPDEVICEID' in interface:
                    interface['DESCRIPTION'] = self._get_win32_interface_id(
                        interface['PNPDEVICEID']
                    )
        
        # Filter out loopback and interfaces without required info
        filtered_interfaces = [
            iface for iface in interfaces
            if iface.get('DESCRIPTION') != 'lo'
            and iface.get('IPADDRESS')
            and iface.get('MACADDR')
        ]
        
        return filtered_interfaces
    
    def _get_payload(self, target: str) -> bytes:
        """
        Generate the Wake-on-LAN magic packet payload.
        
        Args:
            target: MAC address (12 hex characters, no separators)
        
        Returns:
            Magic packet bytes
        """
        # Magic packet is FF FF FF FF FF FF followed by MAC address 16 times
        mac_bytes = bytes.fromhex(target)
        return b'\xff' * 6 + mac_bytes * 16
    
    def _get_win32_interface_id(self, pnpid: str) -> Optional[str]:
        """
        Get Windows interface ID from PnP ID.
        Windows-specific functionality.
        """
        try:
            # Would import from GLPI.Agent.Tools.Win32
            # key = get_registry_key(
            #     path="HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/Control/Network"
            # )
            key = {}  # Placeholder
            
            for subkey_id, subkey in key.items():
                # We're only interested in GUID subkeys
                if not re.match(r'^\{.+\}/$', subkey_id):
                    continue
                
                for subsubkey_id, subsubkey in subkey.items():
                    if 'Connection/' not in subsubkey:
                        continue
                    
                    connection = subsubkey.get('Connection/', {})
                    if connection.get('/PnpInstanceID') != pnpid:
                        continue
                    
                    device_id = subsubkey_id.rstrip('/')
                    return f'\\Device\\NPF_{device_id}'
            
        except Exception:
            pass
        
        return None
