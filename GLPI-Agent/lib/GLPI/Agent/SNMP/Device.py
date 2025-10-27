"""
GLPI Agent SNMP Device Module

This module provides the Device class for handling SNMP device discovery and inventory
operations. It is a Python conversion of the Perl GLPI::Agent::SNMP::Device module.

The module supports:
- Network device discovery with SNMP
- Device inventory collection
- MIB support for various device types
- Component and hardware information extraction

Author: Converted from Perl to Python
License: Compatible with GLPI Agent
"""

import re
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict


class SNMPDevice:
    """
    GLPI Agent SNMP Device class for network device discovery and inventory.
    
    This class provides methods to interact with SNMP-enabled devices to collect
    information for discovery and inventory purposes. It acts as a wrapper around
    SNMP operations and provides standardized methods for data extraction.
    
    Attributes:
        snmp: SNMP session object for device communication
        glpi: GLPI server version string for feature support checking
        nowalk: Boolean flag to disable SNMP walk operations
        logger: Logger instance for debugging and information
        MIBSUPPORT: MIB support handler instance
        
    Supported discovery info fields (from protocol specification):
        DESCRIPTION, FIRMWARE, ID, IPS, LOCATION, MAC, MEMORY, MODEL,
        SNMPHOSTNAME, TYPE, SERIAL, UPTIME, MANUFACTURER, CONTACT, AUTHSNMP
        
    Supported inventory info fields (from protocol specification):
        INFO, PORTS, MODEMS, FIRMWARES, SIMCARDS, PAGECOUNTERS, 
        CARTRIDGES, COMPONENTS, STORAGES, DRIVES
    """
    
    # Class constants defining supported information types
    DISCOVERY_FIELDS = [
        'DESCRIPTION', 'FIRMWARE', 'ID', 'IPS', 'LOCATION', 'MAC', 
        'MEMORY', 'MODEL', 'SNMPHOSTNAME', 'TYPE', 'SERIAL', 'UPTIME', 
        'MANUFACTURER', 'CONTACT', 'AUTHSNMP'
    ]
    
    INVENTORY_FIELDS = [
        'INFO', 'PORTS', 'MODEMS', 'FIRMWARES', 'SIMCARDS', 
        'PAGECOUNTERS', 'CARTRIDGES', 'COMPONENTS', 'STORAGES', 'DRIVES'
    ]
    
    # Common base variables with OIDs and types for SNMP queries
    BASE_VARIABLES = {
        'SNMPHOSTNAME': {
            'oid': [
                '.1.3.6.1.2.1.1.5.0',  # Standard sysName
                '.1.3.6.1.4.1.2699.1.2.1.2.1.1.2.1',  # PRINTER-PORT-MONITOR-MIB
            ],
            'type': 'string',
        },
        'LOCATION': {
            'oid': '.1.3.6.1.2.1.1.6.0',  # sysLocation
            'type': 'string',
        },
        'CONTACT': {
            'oid': '.1.3.6.1.2.1.1.4.0',  # sysContact
            'type': 'string',
        },
        'UPTIME': {
            'oid': '.1.3.6.1.2.1.1.3.0',  # sysUpTime
            'type': 'string',
        },
    }
    
    # Inventory-only base variables
    INVENTORY_BASE_VARIABLES = {
        'CPU': {
            'oid': [
                '.1.3.6.1.4.1.9.9.109.1.1.1.1.6.1',  # Cisco CPU 5min average
                '.1.3.6.1.4.1.9.9.109.1.1.1.1.3.1',  # Cisco CPU 1min average
            ],
            'type': 'count',
        },
        'MEMORY': {
            'oid': '.1.3.6.1.2.1.25.2.3.1.5.1',  # HOST-RESOURCES-MIB
            'type': 'memory',
        },
        'RAM': {
            'oid': {
                '.1.3.6.1.4.1.2021.4.5': 'kb',      # NET-SNMP-MIB memTotalReal
                '.1.3.6.1.4.1.9.3.6.6.0': 'bytes',  # Cisco memory
                '.1.3.6.1.2.1.25.2.2.0': 'kb',      # HOST-RESOURCES-MIB
            },
            'type': 'memory',
        },
    }
    
    # Rules for manufacturer identification based on model name
    SYSMODEL_FIRST_WORD = {
        'dell': {'manufacturer': 'Dell'},
    }
    
    # MAC address pattern for validation
    MAC_ADDRESS_PATTERN = r'^[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}$'
    
    def __init__(self, snmp=None, glpi='', logger=None, **params):
        """
        Initialize the SNMP Device instance.
        
        Args:
            snmp: SNMP session object (mandatory)
            glpi: GLPI server version string for feature support checking
            logger: Logger instance for debugging
            **params: Additional parameters
            
        Raises:
            ValueError: If snmp parameter is not provided
        """
        if not snmp:
            raise ValueError("SNMP session object is required")
        
        self.snmp = snmp
        self.glpi = glpi or ''
        self.nowalk = False  # Can be set to disable walk API
        self.logger = logger
        self.MIBSUPPORT = None
        
        # Initialize data containers
        self._init_data_containers()
    
    def _init_data_containers(self):
        """Initialize internal data containers for device information."""
        self.COMPONENTS = {'COMPONENT': []}
        self.MODEMS = []
        self.FIRMWARES = []
        self.SIMCARDS = []
        self.PORTS = {'PORT': {}}
        self.INFO = {}
        self.IPS = {}
    
    def get(self, oid: str) -> Optional[Any]:
        """
        Perform SNMP GET operation on a single OID.
        
        Args:
            oid: The OID string to query
            
        Returns:
            The value retrieved from the device, or None if failed
        """
        if not self.snmp or not oid:
            return None
        
        return self.snmp.get(oid)
    
    def walk(self, oid: str) -> Optional[Dict[str, Any]]:
        """
        Perform SNMP WALK operation on an OID tree.
        
        Args:
            oid: The root OID string to walk
            
        Returns:
            Dictionary of OID -> value mappings, or None if failed or disabled
        """
        if self.nowalk:
            return None
        
        if not self.snmp or not oid:
            return None
        
        return self.snmp.walk(oid)
    
    def disable_walk(self):
        """
        Disable SNMP walk operations.
        
        Useful for devices that don't support walk operations properly,
        such as some Snom phones.
        """
        self.nowalk = True
    
    def switch_vlan_context(self, vlan_id: Union[int, str]) -> Optional[Any]:
        """
        Switch SNMP context to a specific VLAN.
        
        Args:
            vlan_id: VLAN ID to switch to
            
        Returns:
            Result of the context switch operation
        """
        if not self.snmp or not vlan_id:
            return None
        
        return self.snmp.switch_vlan_context(vlan_id)
    
    def reset_original_context(self) -> Optional[Any]:
        """
        Reset SNMP context to the original state.
        
        Returns:
            Result of the context reset operation
        """
        if not self.snmp:
            return None
        
        return self.snmp.reset_original_context()
    
    def load_mib_support(self, sysobjectid: str, config=None):
        """
        Load MIB support for the device based on its sysObjectID.
        
        This method initializes the MIB support handler which provides
        device-specific methods for information extraction.
        
        Args:
            sysobjectid: System Object ID from SNMP
            config: Configuration dictionary for plugins
        """
        # Import here to avoid circular dependencies
        from mib_support import MibSupport
        
        self.MIBSUPPORT = MibSupport(
            sysobjectid=sysobjectid,
            device=self,
            config=config,
            logger=self.logger
        )
    
    def run_mib_support(self):
        """Execute MIB-specific support methods if available."""
        if self.MIBSUPPORT:
            self.MIBSUPPORT.run()
    
    def get_serial_by_mib_support(self) -> Optional[str]:
        """
        Get device serial number using MIB support.
        
        Returns:
            Serial number string or None
        """
        if not self.MIBSUPPORT:
            return None
        
        return self.MIBSUPPORT.get_method('getSerial')
    
    def get_firmware_by_mib_support(self) -> Optional[str]:
        """
        Get device firmware version using MIB support.
        
        Returns:
            Firmware version string or None
        """
        if not self.MIBSUPPORT:
            return None
        
        return self.MIBSUPPORT.get_method('getFirmware')
    
    def get_firmware_date_by_mib_support(self) -> Optional[str]:
        """
        Get device firmware date using MIB support.
        
        Returns:
            Canonical date string or None
        """
        if not self.MIBSUPPORT:
            return None
        
        date = self.MIBSUPPORT.get_method('getFirmwareDate')
        return self._get_canonical_date(date) if date else None
    
    def get_mac_address_by_mib_support(self) -> Optional[str]:
        """
        Get device MAC address using MIB support.
        
        Returns:
            MAC address string or None
        """
        if not self.MIBSUPPORT:
            return None
        
        return self.MIBSUPPORT.get_method('getMacAddress')
    
    def get_ip_by_mib_support(self) -> Optional[str]:
        """
        Get device IP address using MIB support.
        
        Returns:
            IP address string or None
        """
        if not self.MIBSUPPORT:
            return None
        
        return self.MIBSUPPORT.get_method('getIp')
    
    def get_discovery_info(self) -> Dict[str, Any]:
        """
        Get filtered discovery information.
        
        Returns a dictionary containing only the fields relevant for
        device discovery as defined in the protocol specification.
        
        Returns:
            Dictionary with discovery information
        """
        info = {}
        
        for info_key in self.DISCOVERY_FIELDS:
            if hasattr(self, info_key):
                info[info_key] = getattr(self, info_key)
        
        return info
    
    def get_inventory(self) -> Dict[str, Any]:
        """
        Get filtered inventory information.
        
        Returns a dictionary containing only the fields relevant for
        device inventory as defined in the protocol specification.
        
        Returns:
            Dictionary with inventory information
        """
        inventory = {}
        
        for info_key in self.INVENTORY_FIELDS:
            if hasattr(self, info_key):
                inventory[info_key] = getattr(self, info_key)
        
        return inventory
    
    def add_component(self, component: Dict[str, Any]):
        """
        Add a hardware component to the device inventory.
        
        Args:
            component: Dictionary containing component information
        """
        if not self._clean_hash(component):
            return
        
        self.COMPONENTS['COMPONENT'].append(component)
    
    def add_modem(self, modem: Dict[str, Any]):
        """
        Add a modem to the device inventory.
        
        Args:
            modem: Dictionary containing modem information
        """
        if not self._clean_hash(modem):
            return
        
        self.MODEMS.append(modem)
    
    def add_firmware(self, firmware: Dict[str, Any]):
        """
        Add firmware information to the device inventory.
        
        Args:
            firmware: Dictionary containing firmware information
        """
        if not self._clean_hash(firmware):
            return
        
        self.FIRMWARES.append(firmware)
    
    def add_simcard(self, simcard: Dict[str, Any]):
        """
        Add a SIM card to the device inventory.
        
        Args:
            simcard: Dictionary containing SIM card information
        """
        if not self._clean_hash(simcard):
            return
        
        self.SIMCARDS.append(simcard)
    
    def add_port(self, **ports):
        """
        Add network ports to the device inventory.
        
        Args:
            **ports: Keyword arguments where key is port identifier and 
                     value is dictionary with port information
        """
        for port_id, port_info in ports.items():
            if not self._clean_hash(port_info):
                continue
            
            self.PORTS['PORT'][port_id] = port_info
    
    @staticmethod
    def _clean_hash(hashref: Any) -> int:
        """
        Clean a dictionary by removing None values.
        
        Args:
            hashref: Dictionary to clean
            
        Returns:
            Number of keys remaining after cleaning, 0 if not a dict
        """
        if not isinstance(hashref, dict):
            return 0
        
        keys_to_remove = [k for k, v in hashref.items() if v is None]
        for key in keys_to_remove:
            del hashref[key]
        
        return len(hashref)
    
    def set_serial(self):
        """
        Set the device serial number.
        
        Attempts multiple methods in order:
        1. MIB support mechanism
        2. Device-specific OIDs based on device type
        3. Standard ENTITY-MIB OIDs
        """
        # Try MIB Support first
        serial = self.get_serial_by_mib_support()
        
        if not serial and hasattr(self, 'TYPE'):
            # Type-specific OID attempts
            if self.TYPE == 'PRINTER':
                serial = self.get('.1.3.6.1.2.1.43.5.1.1.17.1')
            elif self.TYPE == 'NETWORKING':
                serial = self.get('.1.3.6.1.4.1.9.3.6.3.0')  # Cisco
        
        # Standard ENTITY-MIB fallback
        if not serial:
            serial = self._get_first('.1.3.6.1.2.1.47.1.1.1.1.11')
        
        if serial:
            self.SERIAL = self._get_canonical_string(serial)
    
    def set_mac(self):
        """
        Set the device MAC address.
        
        This method implements a sophisticated algorithm to determine the
        primary MAC address of a device:
        1. Try MIB support mechanism
        2. Check peer MAC addresses for gateway
        3. Get all MAC addresses from interfaces
        4. Filter and validate MAC addresses
        5. Find the first manufacturer-assigned MAC (consecutive MACs)
        6. Fallback to first interface with speed configured
        """
        # Try MIB support first
        mac = self.get_mac_address_by_mib_support()
        if mac and re.match(self.MAC_ADDRESS_PATTERN, mac, re.IGNORECASE):
            self.MAC = mac
            return
        
        # Get IP and MAC address mappings
        addresses = self.walk('.1.3.6.1.2.1.2.2.1.6')  # ifPhysAddress
        ips = self._get_ip_interface_mapping()
        
        if not addresses:
            return
        
        # Try to get MAC from peer (gateway)
        peers = self._get_peer_addresses()
        if peers and ips:
            for peer in peers:
                if peer in ips and ips[peer] in addresses:
                    address = self._get_canonical_mac_address(addresses[ips[peer]])
                    if address and re.match(self.MAC_ADDRESS_PATTERN, address, re.IGNORECASE):
                        self.MAC = address
                        return
        
        # Get all MAC addresses
        all_mac_addresses = []
        
        # First try IP-filtered list
        if ips:
            all_mac_addresses = [addresses[idx] for idx in ips.values() 
                               if idx in addresses and addresses[idx]]
        
        # Fallback to all addresses
        if not all_mac_addresses:
            all_mac_addresses = [addr for addr in addresses.values() if addr]
        
        # Filter valid MAC addresses
        valid_mac_addresses = []
        seen = set()
        
        for addr in all_mac_addresses:
            canonical = self._get_canonical_mac_address(addr)
            if (canonical and 
                canonical not in seen and
                canonical != '00:00:00:00:00:00' and
                re.match(self.MAC_ADDRESS_PATTERN, canonical, re.IGNORECASE)):
                valid_mac_addresses.append(canonical)
                seen.add(canonical)
        
        if not valid_mac_addresses:
            return
        
        # If only one valid MAC, use it
        if len(valid_mac_addresses) == 1:
            self.MAC = valid_mac_addresses[0]
            return
        
        # Find first consecutive MAC pair (manufacturer-assigned)
        mac_numbers = {mac: self._numeric_mac(mac) for mac in valid_mac_addresses}
        sorted_macs = sorted(valid_mac_addresses, key=lambda m: mac_numbers[m])
        
        for i in range(len(sorted_macs) - 1):
            current_mac = sorted_macs[i]
            next_mac = sorted_macs[i + 1]
            if mac_numbers[current_mac] == mac_numbers[next_mac] - 1:
                self.MAC = current_mac
                return
        
        # Try to find first interface with speed set
        if_speed = self.walk('.1.3.6.1.2.1.2.2.1.5')  # ifSpeed
        if if_speed:
            for index in sorted(if_speed.keys(), key=int):
                if not if_speed[index] or index not in addresses:
                    continue
                
                current_mac = self._get_canonical_mac_address(addresses[index])
                if current_mac and current_mac in valid_mac_addresses:
                    self.MAC = current_mac
                    return
    
    def set_model(self):
        """
        Set the device model and manufacturer.
        
        Attempts multiple methods:
        1. Type-specific OIDs (printer, UPS, etc.)
        2. Standard ENTITY-MIB
        3. Manufacturer identification from generic OIDs
        4. Rule-based manufacturer detection from model name
        5. MIB support override
        """
        # Fallback model identification
        if not hasattr(self, 'MODEL'):
            model = None
            
            if hasattr(self, 'TYPE'):
                if self.TYPE == 'PRINTER':
                    model = self.get('.1.3.6.1.2.1.25.3.2.1.3.1')
                elif self.TYPE == 'POWER':
                    model = self.get('.1.3.6.1.2.1.33.1.1.5.0')  # UPS-MIB
            
            if not model:
                model = self._get_first('.1.3.6.1.2.1.47.1.1.1.1.13')
            
            if model:
                self.MODEL = self._get_canonical_string(model)
        
        # Fallback manufacturer identification
        if not hasattr(self, 'MANUFACTURER'):
            manufacturer = self.get('.1.3.6.1.2.1.43.8.2.1.14.1.1')
            if manufacturer:
                self.MANUFACTURER = manufacturer
        
        # Reset manufacturer by rule based on model first word
        if hasattr(self, 'MODEL') and self.MODEL:
            match = re.match(r'(\S+)', self.MODEL)
            if match:
                first_word = match.group(1).lower()
                if first_word in self.SYSMODEL_FIRST_WORD:
                    result = self.SYSMODEL_FIRST_WORD[first_word]
                    if 'manufacturer' in result:
                        self.MANUFACTURER = result['manufacturer']
        
        # Permit MIB support to override model
        if self.MIBSUPPORT:
            model = self.MIBSUPPORT.get_method('getModel')
            if model:
                self.MODEL = self._get_canonical_string(model)
    
    def set_type(self):
        """Set the device type using MIB support if available."""
        if self.MIBSUPPORT:
            device_type = self.MIBSUPPORT.get_method('getType')
            if device_type:
                self.TYPE = device_type
    
    def set_manufacturer(self):
        """Set the device manufacturer using MIB support if available."""
        if self.MIBSUPPORT:
            manufacturer = self.MIBSUPPORT.get_method('getManufacturer')
            if manufacturer:
                self.MANUFACTURER = manufacturer
    
    def set_base_infos(self):
        """
        Set basic device information from standard SNMP OIDs.
        
        Retrieves: SNMPHOSTNAME, LOCATION, CONTACT, UPTIME
        Filters out default/template values from LOCATION and CONTACT.
        """
        self._set_from_oid_list(self.BASE_VARIABLES, self.__dict__)
        
        # Filter out unwanted default values
        if hasattr(self, 'LOCATION') and self.LOCATION:
            if re.search(r'edit /etc.*snmp.*\.conf', self.LOCATION):
                delattr(self, 'LOCATION')
        
        if hasattr(self, 'CONTACT') and self.CONTACT:
            if re.search(r'configure /etc.*snmp.*\.conf', self.CONTACT):
                delattr(self, 'CONTACT')
    
    def set_snmp_hostname(self):
        """Set the SNMP hostname using MIB support if available."""
        if self.MIBSUPPORT:
            name = self.MIBSUPPORT.get_method('getSnmpHostname')
            if name:
                self.SNMPHOSTNAME = name
    
    def set_inventory_base_infos(self):
        """Set inventory-specific base information (CPU, MEMORY, RAM)."""
        self._set_from_oid_list(self.INVENTORY_BASE_VARIABLES, self.INFO)
    
    def _set_from_oid_list(self, oid_list: Dict, target_dict: Dict):
        """
        Set values from a list of OID definitions.
        
        Args:
            oid_list: Dictionary of field definitions with OIDs and types
            target_dict: Target dictionary to store the results
        """
        for key, variable in oid_list.items():
            var_type = variable['type']
            oid = variable['oid']
            raw_value = None
            
            # Handle list of OIDs
            if isinstance(oid, list):
                for single_oid in oid:
                    raw_value = self.get(single_oid)
                    if raw_value and var_type in ('memory', 'count'):
                        # Skip if no number present
                        if not re.search(r'\d+', str(raw_value)):
                            raw_value = None
                    if raw_value is not None:
                        break
            
            # Handle dict of OIDs with units
            elif isinstance(oid, dict):
                for single_oid, unit in oid.items():
                    raw_value = self.get(single_oid)
                    if raw_value and var_type in ('memory', 'count'):
                        if not re.search(r'\d+', str(raw_value)):
                            raw_value = None
                        elif unit == 'kb' and self._is_integer(str(raw_value)):
                            raw_value = f"{raw_value} kB"
                    if raw_value is not None:
                        break
            
            # Handle single OID string
            else:
                raw_value = self.get(oid)
            
            if raw_value is None:
                continue
            
            # Convert value based on type
            if var_type == 'memory':
                value = self._get_canonical_memory(raw_value)
            elif var_type == 'string':
                value = self._get_canonical_string(raw_value)
            elif var_type == 'count':
                value = self._get_canonical_count(raw_value)
            else:
                value = raw_value
            
            if value is not None:
                target_dict[key] = value
    
    @staticmethod
    def _numeric_mac(mac: str) -> int:
        """
        Convert MAC address to numeric value for sorting.
        
        Args:
            mac: MAC address in format "aa:bb:cc:dd:ee:ff"
            
        Returns:
            Integer representation of MAC address
        """
        number = 0
        multiplicator = 1
        
        parts = mac.split(':')
        while parts:
            number += int(parts.pop(), 16) * multiplicator
            multiplicator <<= 8
        
        return number
    
    def set_ip(self):
        """
        Set the device IP address(es).
        
        Tries multiple methods:
        1. Standard IP-MIB ipAdEntAddr table (IPv4)
        2. IP-MIB ipAddressTable (IPv4 and IPv6)
        3. MIB support mechanism
        """
        # Try standard ipAdEntAddr
        results = self.walk('.1.3.6.1.2.1.4.20.1.1')
        if results:
            self.IPS = {'IP': sorted(results.values())}
            return
        
        # Try IP-MIB ipAddressTable
        ip_address_if_index = self.walk('.1.3.6.1.2.1.4.34.1.3')
        if ip_address_if_index:
            ip_address_type = self.walk('.1.3.6.1.2.1.4.34.1.4')
            if ip_address_type:
                # Filter for unicast addresses (type 1)
                keys = [k for k, v in ip_address_type.items() if v == 1]
                ips = []
                
                for key in keys:
                    parts = key.split('.')
                    if len(parts) < 2:
                        continue
                    
                    addr_type = int(parts[0])
                    addr_len = int(parts[1])
                    data = [int(p) for p in parts[2:]]
                    
                    # IPv4
                    if addr_type == 1 and addr_len == 4:
                        if data[0] == 127:  # Skip localhost
                            continue
                        ips.append('.'.join(map(str, data)))
                    
                    # IPv6
                    elif addr_type == 2 and addr_len == 16:
                        if data[0] == 0:  # Skip localhost
                            continue
                        # Convert to hex pairs
                        hex_pairs = [
                            hex(data[i*2]*256 + data[i*2+1])[2:] 
                            for i in range(8)
                        ]
                        ipv6 = ':'.join(hex_pairs)
                        ipv6 = re.sub(r'::+', '::', ipv6)
                        ips.append(ipv6)
                
                if ips:
                    self.IPS = {'IP': sorted(ips)}
                    return
        
        # Try MIB support
        ip = self.get_ip_by_mib_support()
        if ip:
            self.IPS = {'IP': [ip]}
    
    def set_components(self):
        """
        Set device components from ENTITY-MIB and MIB support.
        
        Components include physical inventory items like:
        - Chassis
        - Modules
        - Power supplies
        - Fans
        - etc.
        """
        # Try standard ENTITY-MIB first
        try:
            from components import Components
            components = Components(device=self)
            if components:
                for component in components.get_physical_components():
                    self.add_component(component)
        except ImportError:
            pass
        
        # Try MIB support plugins
        if self.MIBSUPPORT:
            components = self.MIBSUPPORT.get_method('getComponents') or []
            for component in components:
                self.add_component(component)
    
    # Helper methods for data conversion and validation
    
    def _get_first(self, oid: str) -> Optional[Any]:
        """
        Get first value from an OID walk.
        
        Args:
            oid: OID to walk
            
        Returns:
            First value found or None
        """
        results = self.walk(oid)
        if results:
            return next(iter(results.values()), None)
        return None
    
    def _get_ip_interface_mapping(self) -> Dict[str, int]:
        """
        Get mapping of IP addresses to interface indices.
        
        Returns:
            Dictionary mapping IP -> interface index
        """
        results = self.walk('.1.3.6.1.2.1.4.20.1.2')  # ipAdEntIfIndex
        return results if results else {}
    
    def _get_peer_addresses(self) -> List[str]:
        """
        Get peer IP addresses (typically gateway).
        
        Returns:
            List of peer IP addresses
        """
        # Implementation depends on routing table access
        # Simplified version
        return []
    
    @staticmethod
    def _get_canonical_string(value: Any) -> str:
        """
        Convert value to canonical string format.
        
        Args:
            value: Value to convert
            
        Returns:
            Cleaned string value
        """
        if value is None:
            return ''
        
        string = str(value).strip()
        # Remove null bytes and control characters
        string = ''.join(c for c in string if ord(c) >= 32 or c in '\n\r\t')
        return string
    
    @staticmethod
    def _get_canonical_mac_address(value: Any) -> Optional[str]:
        """
        Convert value to canonical MAC address format.
        
        Args:
            value: Value to convert (hex string or bytes)
            
        Returns:
            MAC address in format "aa:bb:cc:dd:ee:ff" or None
        """
        if not value:
            return None
        
        # Handle byte array
        if isinstance(value, (bytes, bytearray)):
            if len(value) == 6:
                return ':'.join(f'{b:02x}' for b in value)
        
        # Handle string representation
        string = str(value)
        
        # Remove common separators
        clean = re.sub(r'[:-]', '', string)
        
        # Convert to MAC format
        if len(clean) == 12 and all(c in '0123456789abcdefABCDEF' for c in clean):
            return ':'.join(clean[i:i+2].lower() for i in range(0, 12, 2))
        
        return None
    
    @staticmethod
    def _get_canonical_memory(value: Any) -> Optional[int]:
        """
        Convert memory value to MB.
        
        Args:
            value: Memory value with optional unit suffix
            
        Returns:
            Memory in MB or None
        """
        if not value:
            return None
        
        string = str(value).strip()
        
        # Extract number and unit
        match = re.match(r'([\d.]+)\s*([A-Za-z]*)', string)
        if not match:
            return None
        
        number = float(match.group(1))
        unit = match.group(2).lower()
        
        # Convert to MB
        if unit in ('kb', 'kib'):
            return int(number / 1024)
        elif unit in ('mb', 'mib', ''):
            return int(number)
        elif unit in ('gb', 'gib'):
            return int(number * 1024)
        elif unit in ('tb', 'tib'):
            return int(number * 1024 * 1024)
        elif unit == 'bytes':
            return int(number / (1024 * 1024))
        
        # Default: assume bytes
        return int(number / (1024 * 1024))
    
    @staticmethod
    def _get_canonical_count(value: Any) -> Optional[int]:
        """
        Extract count/number from value.
        
        Args:
            value: Value to parse
            
        Returns:
            Integer count or None
        """
        if not value:
            return None
        
        match = re.search(r'(\d+)', str(value))
        return int(match.group(1)) if match else None
    
    @staticmethod
    def _get_canonical_date(value: Any) -> Optional[str]:
        """
        Convert date to canonical format.
        
        Args:
            value: Date value to convert
            
        Returns:
            Date in ISO format or None
        """
        if not value:
            return None
        
        # Implementation depends on date format handling requirements
        # Simplified version returns string as-is
        return str(value)
    
    @staticmethod
    def _is_integer(value: str) -> bool:
        """
        Check if string represents an integer.
        
        Args:
            value: String to check
            
        Returns:
            True if value is an integer
        """
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False


# Example usage
if __name__ == "__main__":
    """
    Example demonstrating how to use the SNMPDevice class.
    
    Note: This requires a working SNMP session object which would typically
    come from a library like pysnmp or easysnmp.
    """
    
    # This is pseudocode showing typical usage
    print("SNMPDevice class for network device discovery and inventory")
    print("="*60)
    print("\nTypical usage pattern:")
    print("""
    # 1. Create SNMP session (using pysnmp or similar)
    from pysnmp import SNMP
    snmp_session = SNMP(host='192.168.1.1', community='public')
    
    # 2. Create device instance
    device = SNMPDevice(snmp=snmp_session, logger=my_logger)
    
    # 3. Load MIB support based on sysObjectID
    sysobjectid = snmp_session.get('.1.3.6.1.2.1.1.2.0')
    device.load_mib_support(sysobjectid)
    
    # 4. Collect device information
    device.set_base_infos()
    device.set_serial()
    device.set_mac()
    device.set_model()
    device.set_ip()
    device.set_components()
    
    # 5. Get discovery or inventory data
    discovery_info = device.get_discovery_info()
    inventory_data = device.get_inventory()
    
    # 6. Process the collected data
    print(f"Device: {discovery_info.get('MODEL')}")
    print(f"Serial: {discovery_info.get('SERIAL')}")
    print(f"MAC: {discovery_info.get('MAC')}")
    """)
