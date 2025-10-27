"""
SNMP Mock Client

This module provides a mock SNMP client for replaying SNMP queries from snmpwalk files.
It simulates SNMP operations without requiring actual network connectivity to SNMP agents.
"""

import re
from typing import Dict, List, Optional, Tuple, Any, Union


class SNMPMock:
    """
    Mock SNMP client for testing and development.
    
    This class simulates SNMP operations by reading pre-recorded snmpwalk output
    from files or accepting data structures directly. It supports both symbolic
    and numerical OID formats.
    
    Attributes:
        _ip (str): IP address of the simulated SNMP agent
        _file (str): Path to the snmpwalk file
        _walk (dict): Internal tree structure storing SNMP data
        _oldwalk (dict): Backup of walk data for VLAN context switching
    """
    
    # OID prefix mappings for converting symbolic names to numerical OIDs
    PREFIXES = {
        'iso': '.1',
        'SNMPv2-MIB::sysDescr': '.1.3.6.1.2.1.1.1',
        'SNMPv2-MIB::sysObjectID': '.1.3.6.1.2.1.1.2',
        'SNMPv2-MIB::sysUpTime': '.1.3.6.1.2.1.1.3',
        'SNMPv2-MIB::sysContact': '.1.3.6.1.2.1.1.4',
        'SNMPv2-MIB::sysName': '.1.3.6.1.2.1.1.5',
        'SNMPv2-MIB::sysLocation': '.1.3.6.1.2.1.1.6',
        'SNMPv2-MIB::sysORID': '.1.3.6.1.2.1.1.9.1.2',
        'SNMPv2-SMI::mib-2': '.1.3.6.1.2.1',
        'SNMPv2-SMI::enterprises': '.1.3.6.1.4.1',
        'IF-MIB::ifIndex': '.1.3.6.1.2.1.2.2.1.1',
        'IF-MIB::ifDescr': '.1.3.6.1.2.1.2.2.1.2',
        'IF-MIB::ifType': '.1.3.6.1.2.1.2.2.1.3',
        'IF-MIB::ifMtu': '.1.3.6.1.2.1.2.2.1.4',
        'IF-MIB::ifSpeed': '.1.3.6.1.2.1.2.2.1.5',
        'IF-MIB::ifPhysAddress': '.1.3.6.1.2.1.2.2.1.6',
        'IF-MIB::ifLastChange': '.1.3.6.1.2.1.2.2.1.9',
        'IF-MIB::ifInOctets': '.1.3.6.1.2.1.2.2.1.10',
        'IF-MIB::ifInErrors': '.1.3.6.1.2.1.2.2.1.14',
        'IF-MIB::ifOutOctets': '.1.3.6.1.2.1.2.2.1.16',
        'IF-MIB::ifOutErrors': '.1.3.6.1.2.1.2.2.1.20',
        'IF-MIB::ifName': '.1.3.6.1.2.1.31.1.1.1.1',
        'HOST-RESOURCES-MIB::hrDeviceDescr': '.1.3.6.1.2.1.25.3.2.1.3',
        'NET-SNMP-MIB::netSnmpAgentOIDs': '.1.3.6.1.4.1.8072.3.2',
        'ENTITY-MIB::entPhysicalIndex': '.1.3.6.1.2.1.47.1.1.1.1.1',
        'ENTITY-MIB::entPhysicalDescr': '.1.3.6.1.2.1.47.1.1.1.1.2',
        'ENTITY-MIB::entPhysicalContainedIn': '.1.3.6.1.2.1.47.1.1.1.1.4',
        'ENTITY-MIB::entPhysicalClass': '.1.3.6.1.2.1.47.1.1.1.1.5',
        'ENTITY-MIB::entPhysicalName': '.1.3.6.1.2.1.47.1.1.1.1.7',
        'ENTITY-MIB::entPhysicalHardwareRev': '.1.3.6.1.2.1.47.1.1.1.1.8',
        'ENTITY-MIB::entPhysicalFirmwareRev': '.1.3.6.1.2.1.47.1.1.1.1.9',
        'ENTITY-MIB::entPhysicalSoftwareRev': '.1.3.6.1.2.1.47.1.1.1.1.10',
        'ENTITY-MIB::entPhysicalSerialNum': '.1.3.6.1.2.1.47.1.1.1.1.11',
        'ENTITY-MIB::entPhysicalMfgName': '.1.3.6.1.2.1.47.1.1.1.1.12',
        'ENTITY-MIB::entPhysicalModelName': '.1.3.6.1.2.1.47.1.1.1.1.13',
        'ENTITY-MIB::entPhysicalIsFRU': '.1.3.6.1.2.1.47.1.1.1.1.16',
    }
    
    def __init__(self, ip: Optional[str] = None, file: Optional[str] = None, 
                 hash: Optional[Dict[str, Any]] = None):
        """
        Initialize the mock SNMP client.
        
        Args:
            ip: IP address of the simulated SNMP agent
            file: Path to snmpwalk output file to load
            hash: Dictionary of OID -> value mappings to load directly
            
        Raises:
            FileNotFoundError: If the specified file doesn't exist
            PermissionError: If the specified file isn't readable
            ValueError: If neither file nor hash is provided
        """
        self._ip = ip
        self._file = None
        self._walk = {}
        self._oldwalk = None
        
        if file:
            # Validate file exists and is readable
            try:
                with open(file, 'r') as f:
                    pass
            except FileNotFoundError:
                raise FileNotFoundError(f"non-existing file '{file}'")
            except PermissionError:
                raise PermissionError(f"unreadable file '{file}'")
            
            self._file = file
            self._set_indexed_values()
            
        elif hash:
            self._walk = {}
            for oid, value in hash.items():
                self._set_value(oid, value)
    
    def switch_vlan_context(self, vlan_id: int) -> None:
        """
        Switch to a different VLAN context for SNMP queries.
        
        This method is used in managed switch environments where different VLANs
        may have different SNMP data. It attempts to load a VLAN-specific walk file.
        
        Args:
            vlan_id: VLAN ID to switch to
        """
        # Backup current walk if not already backed up
        if not self._oldwalk:
            self._oldwalk = self._walk
        
        # Try to load VLAN-specific file
        vlan_file = f"{self._file}@{vlan_id}"
        try:
            with open(vlan_file, 'r') as f:
                pass
            self._set_indexed_values(vlan_file)
        except (FileNotFoundError, PermissionError):
            # If VLAN file doesn't exist, clear the walk
            self._walk = {}
    
    def reset_original_context(self) -> None:
        """
        Reset to the original SNMP context after VLAN switching.
        
        This restores the walk data that was active before any VLAN context switches.
        """
        if self._oldwalk:
            self._walk = self._oldwalk
            self._oldwalk = None
    
    def _set_indexed_values(self, file: Optional[str] = None) -> None:
        """
        Parse an snmpwalk file and build the internal OID tree structure.
        
        This method handles both numerical and symbolic OID formats in the input file.
        It builds an optimized tree structure for efficient OID lookups and walks.
        
        Args:
            file: Path to snmpwalk file (uses self._file if not provided)
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file cannot be read
        """
        file_path = file or self._file
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            raise FileNotFoundError(f"No content found in {file_path} file: {e}")
        
        if not lines:
            raise ValueError(f"No content found in {file_path} file")
        
        # Check first line to determine format
        if not re.match(r'^(\S+) = .*', lines[0]):
            raise ValueError("invalid file format")
        
        # Determine if OIDs are numerical or symbolic
        numerical = lines[0].startswith('.')
        last_value = None
        
        self._walk = {}
        
        for line in lines:
            line = line.rstrip('\n\r')
            
            if numerical:
                # Pattern for numerical OIDs: .1.3.6.1.2.1.1.1.0 = STRING: "value"
                match = re.match(
                    r'^(\S+)\s+=\s+(?:Wrong\s+Type\s+\(should\s+be\s+[^:]+\):\s+)?([^:]+):\s+(.*)',
                    line
                )
                if match:
                    oid, value_type, value = match.groups()
                    last_value = [value_type, value]
                    self._set_value(oid, last_value)
                    continue
            else:
                # Pattern for symbolic OIDs: IF-MIB::ifDescr.1 = STRING: "eth0"
                match = re.match(
                    r'^([^.]+)\.([\d.]+)\s+=\s+(?:Wrong\s+Type\s+\(should\s+be\s+[^:]+\):\s+)?([^:]+):\s+(.*)',
                    line
                )
                if match:
                    mib, suffix, value_type, value = match.groups()
                    
                    if mib in self.PREFIXES:
                        oid = f"{self.PREFIXES[mib]}.{suffix}"
                        last_value = [value_type, value]
                        self._set_value(oid, last_value)
                    else:
                        # Irrelevant OID not in our prefix mapping
                        last_value = None
                    continue
            
            # Check for end-of-walk markers
            if 'No more variables left in this MIB View' in line:
                break
            if line == 'End of MIB':
                break
            
            # Handle multi-line values
            if (line and 
                not line.startswith('=') and 
                line != '= ""' and 
                line != '= STRING:' and 
                last_value):
                
                if (last_value[0] == 'STRING' and 
                    not last_value[1].endswith('"')):
                    last_value[1] += '\n' + line
                    continue
                elif last_value[0] == 'Hex-STRING':
                    last_value[1] += line
                    continue
            
            last_value = None
    
    def _set_value(self, oid: str, value: List[str]) -> None:
        """
        Store a value in the internal OID tree structure.
        
        The tree is optimized by using the first 6 OID components as root keys.
        Each node is represented as: [subnodes, index, index_map, value]
        
        Args:
            oid: Object Identifier in dotted notation (e.g., ".1.3.6.1.2.1.1.1.0")
            value: List containing [type, value] (e.g., ["STRING", "Linux"])
        """
        # Optimization: use first 6 OID digits as tree root
        match = re.match(r'^(\.\d+\.\d+\.\d+\.\d+\.\d+\.\d+)(.*)', oid)
        if not match:
            return
        
        root, remaining = match.groups()
        
        # Initialize root node if it doesn't exist
        # Node structure: [subnodes_list, index, index_map, value]
        if root not in self._walk:
            self._walk[root] = [[], None, {}, None]
        
        base = self._walk[root]
        
        # Traverse/build the tree for remaining OID components
        if remaining:
            for num in remaining.lstrip('.').split('.'):
                num = int(num)
                
                # Check if subnode exists
                if base[2] and num in base[2]:
                    base = base[2][num]
                else:
                    # Create new subnode
                    new_node = [[], num, {}, None]
                    
                    # Initialize subnodes list if needed
                    if base[0] is None:
                        base[0] = []
                    
                    # Add to parent's subnode list and index
                    base[0].append(new_node)
                    base[2][num] = new_node
                    base = new_node
        
        # Store value in leaf node
        base[2] = {}
        base[3] = value
    
    def _get_value(self, oid: str, walk: bool = False) -> Optional[Union[List, Any]]:
        """
        Retrieve a value or node from the internal OID tree.
        
        Args:
            oid: Object Identifier to retrieve
            walk: If True, return the node for walking; if False, return just the value
            
        Returns:
            If walk=True: Node structure for traversal
            If walk=False: [type, value] list or None if not found
        """
        match = re.match(r'^(\.\d+\.\d+\.\d+\.\d+\.\d+\.\d+)(.*)', oid)
        if not match:
            return None
        
        root, remaining = match.groups()
        
        if root not in self._walk:
            return None
        
        base = self._walk[root]
        
        if not remaining:
            return base
        
        # Traverse tree following OID path
        for num in remaining.lstrip('.').split('.'):
            num = int(num)
            
            # Check if path exists
            if not base[2] or num not in base[2]:
                return None
            
            base = base[2][num]
        
        return base if walk else base[3]
    
    def get(self, oid: str) -> Optional[str]:
        """
        Perform an SNMP GET operation for a specific OID.
        
        This is the main method for retrieving individual SNMP values,
        simulating the behavior of an actual SNMP GET request.
        
        Args:
            oid: Object Identifier to retrieve
            
        Returns:
            Sanitized value as string, or None if OID doesn't exist
        """
        if not oid:
            return None
        
        value = self._get_value(oid)
        if not value:
            return None
        
        return self._get_sanitized_value(value[0], value[1])
    
    def walk(self, oid: str) -> Optional[Dict[str, str]]:
        """
        Perform an SNMP WALK operation starting from a given OID.
        
        This simulates SNMP WALK/GETNEXT operations, returning all OID-value
        pairs under the specified OID in the tree hierarchy.
        
        Args:
            oid: Starting Object Identifier for the walk
            
        Returns:
            Dictionary mapping OID suffixes to their values, or None if base OID doesn't exist
        """
        if not oid:
            return None
        
        base = self._get_value(oid, walk=True)
        if not base:
            return None
        
        # Don't walk if no subnodes exist
        if not base[0]:
            return None
        
        return self._deep_walk(base)
    
    @staticmethod
    def _deep_walk(base: List) -> Dict[str, str]:
        """
        Recursively walk through the OID tree and collect all values.
        
        This is a helper method that performs depth-first traversal of the
        tree structure to collect all descendant OID-value pairs.
        
        Args:
            base: Current node in the tree structure
            
        Returns:
            Dictionary mapping relative OID paths to their sanitized values
        """
        result = {}
        
        # Process all subnodes
        for node in base[0]:
            key = str(node[1])
            
            # Store value if present at this node
            if node[3] is not None:
                result[key] = SNMPMock._get_sanitized_value(node[3][0], node[3][1])
            
            # Recursively process subnodes
            if node[0]:
                sub_results = SNMPMock._deep_walk(node)
                for sub_key, sub_value in sub_results.items():
                    result[f"{key}.{sub_key}"] = sub_value
        
        return result
    
    @staticmethod
    def _get_sanitized_value(format_type: str, value: str) -> str:
        """
        Convert raw SNMP values to their proper format.
        
        Different SNMP data types require different processing:
        - Hex strings are converted to 0x-prefixed format
        - Integers may have enumeration labels that need extraction
        - Strings need quote removal
        - OIDs need symbolic-to-numerical conversion
        - Timeticks need special formatting
        
        Args:
            format_type: SNMP data type (STRING, INTEGER, Hex-STRING, OID, etc.)
            value: Raw value string from snmpwalk output
            
        Returns:
            Sanitized value ready for use
        """
        if format_type == 'Hex-STRING':
            # Remove spaces and add 0x prefix
            value = value.replace(' ', '')
            value = f"0x{value}"
            
        elif format_type == 'INTEGER':
            # Extract numeric value from enumeration format: someName(123)
            match = re.match(r'\w+\((\d+)\)', value)
            if match:
                value = match.group(1)
            # Handle special Kbytes format
            match = re.match(r'(-?\d+) Kbytes', value)
            if match:
                value = str(int(match.group(1)) * 1024)
                
        elif format_type == 'STRING':
            # Remove surrounding quotes (but not escaped quotes)
            value = re.sub(r'^(?<!\\)"', '', value)
            value = re.sub(r'(?<!\\)"$', '', value)
            
        elif format_type == 'OID':
            # Convert symbolic OID to numerical format
            match = re.match(r'^([^.]+)(\.[\d.]+)?$', value)
            if match:
                prefix, suffix = match.groups()
                suffix = suffix or ''
                if prefix in SNMPMock.PREFIXES:
                    value = SNMPMock.PREFIXES[prefix] + suffix
                else:
                    value = prefix + suffix
                    
        elif format_type.lower() == 'timeticks':
            # Extract readable time string, removing tick count
            match = re.match(r'^\s*\([\d.]+\)\s*(.*)$', value)
            if match:
                value = match.group(1)
        
        return value
    
    def peer_address(self) -> Optional[str]:
        """
        Get the IP address of the simulated SNMP agent.
        
        Returns:
            IP address string or None if not set
        """
        return self._ip


# Example usage and testing
if __name__ == "__main__":
    # Example 1: Creating mock from a hash
    test_data = {
        '.1.3.6.1.2.1.1.1.0': ['STRING', '"Linux localhost 4.15.0"'],
        '.1.3.6.1.2.1.1.5.0': ['STRING', '"test-server"'],
        '.1.3.6.1.2.1.2.2.1.2.1': ['STRING', '"eth0"'],
        '.1.3.6.1.2.1.2.2.1.2.2': ['STRING', '"eth1"'],
    }
    
    mock = SNMPMock(ip='192.168.1.1', hash=test_data)
    
    # Test GET operation
    print("Testing GET operation:")
    print(f"sysDescr: {mock.get('.1.3.6.1.2.1.1.1.0')}")
    print(f"sysName: {mock.get('.1.3.6.1.2.1.1.5.0')}")
    
    # Test WALK operation
    print("\nTesting WALK operation:")
    results = mock.walk('.1.3.6.1.2.1.2.2.1.2')
    if results:
        for oid, value in results.items():
            print(f"  .1.3.6.1.2.1.2.2.1.2.{oid} = {value}")
    
    print(f"\nPeer address: {mock.peer_address()}")
