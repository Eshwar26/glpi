"""
SNMP MIB Support for TP-Link Devices

This module provides enhanced inventory support for TP-Link network devices,
including switches and routers. It handles firmware detection, VLAN configuration,
hardware information retrieval, and device-specific quirks in TP-Link's SNMP
implementation.
"""

import re
from typing import Dict, List, Optional, Any, Set


class TpLinkMibSupport:
    """
    TP-Link MIB Support Module
    
    This class provides specialized SNMP support for TP-Link networking devices.
    It handles:
    - Hardware and firmware version detection
    - MAC address retrieval
    - Model identification
    - Serial number extraction
    - VLAN configuration parsing
    - Port-VLAN mapping
    
    TP-Link devices have some non-standard SNMP implementations, particularly
    older models that use sysObjectID-based paths instead of standard MIB paths.
    This module handles both newer and legacy implementations.
    
    OID Constants Reference:
    - tplink: .1.3.6.1.4.1.11863 (TP-Link enterprise OID)
    - tplinkMgmt: .1.3.6.1.4.1.11863.6 (Management branch)
    - tplinkSysInfoMIBObjects: .1.3.6.1.4.1.11863.6.1.1 (System info)
    - tplinkDot1qVlanMIBObjects: .1.3.6.1.4.1.11863.6.14.1 (VLAN config)
    """
    
    # System Object ID
    SYS_OBJECT_ID = '.1.3.6.1.2.1.1.2.0'
    
    # TP-Link enterprise MIB base OID
    TPLINK = '.1.3.6.1.4.1.11863'
    
    # Major branches
    SWITCH = TPLINK + '.1'
    TPLINK_MGMT = TPLINK + '.6'
    L2MANAGE_SWITCH = SWITCH + '.1'
    
    # TPLINK-SYSINFO-MIB Objects
    TPLINK_SYSINFO_MIB_OBJECTS = TPLINK_MGMT + '.1.1'
    TP_SYSINFO_HW_VERSION = TPLINK_SYSINFO_MIB_OBJECTS + '.5.0'
    TP_SYSINFO_SW_VERSION = TPLINK_SYSINFO_MIB_OBJECTS + '.6.0'
    TP_SYSINFO_MAC_ADDR = TPLINK_SYSINFO_MIB_OBJECTS + '.7.0'
    TP_SYSINFO_SERIAL_NUM = TPLINK_SYSINFO_MIB_OBJECTS + '.8.0'
    
    # TPLINK-DOT1Q-VLAN-MIB Objects
    TPLINK_DOT1Q_VLAN_MIB_OBJECTS = TPLINK_MGMT + '.14.1'
    
    VLAN_PORT_CONFIG = TPLINK_DOT1Q_VLAN_MIB_OBJECTS + '.1'
    VLAN_CONFIG = TPLINK_DOT1Q_VLAN_MIB_OBJECTS + '.2'
    
    VLAN_PORT_NUMBER = VLAN_PORT_CONFIG + '.1.1.1'
    
    DOT1Q_VLAN_ID = VLAN_CONFIG + '.1.1.1'
    DOT1Q_VLAN_DESCRIPTION = VLAN_CONFIG + '.1.1.2'
    VLAN_TAG_PORT_MEMBER_ADD = VLAN_CONFIG + '.1.1.3'
    VLAN_UNTAG_PORT_MEMBER_ADD = VLAN_CONFIG + '.1.1.4'
    VLAN_PORT_MEMBER_REMOVE = VLAN_CONFIG + '.1.1.5'
    DOT1Q_VLAN_STATUS = VLAN_CONFIG + '.1.1.6'
    
    # MIB support configuration
    MIB_SUPPORT = [
        {
            'name': 'tplink',
            'sysobjectid': TPLINK  # This would be used as a regex pattern
        }
    ]
    
    def __init__(self, snmp_client, device: Optional[Dict] = None):
        """
        Initialize TP-Link MIB support.
        
        Args:
            snmp_client: SNMP client object with get() and walk() methods
            device: Device dictionary to populate with inventory data
        """
        self.snmp = snmp_client
        self.device = device or {}
        self._sysobjectid_cache = None
    
    @staticmethod
    def get_regexp_oid_match(base_oid: str) -> str:
        """
        Generate a regular expression pattern for matching OIDs.
        
        This creates a pattern that matches the base OID and any sub-OIDs.
        Used for device identification based on sysObjectID.
        
        Args:
            base_oid: Base OID to create pattern for
            
        Returns:
            Regular expression pattern string
        """
        # Escape dots for regex and allow any sub-OID
        escaped = base_oid.replace('.', r'\.')
        return f"^{escaped}(\\..*)?$"
    
    def _get_older_sys_info(self, info_suffix: str) -> Optional[str]:
        """
        Retrieve system information from legacy TP-Link devices.
        
        Older TP-Link devices store system information under a path
        constructed from sysObjectID rather than standard MIB locations.
        This method handles that legacy behavior.
        
        The construction is: sysObjectID + ".1.1.1." + info_suffix
        
        Args:
            info_suffix: The specific info identifier (e.g., "6.0" for SW version)
            
        Returns:
            Value from the legacy path, or None if not found
        """
        if not self._sysobjectid_cache:
            self._sysobjectid_cache = self.snmp.get(self.SYS_OBJECT_ID)
        
        if not self._sysobjectid_cache:
            return None
        
        legacy_oid = f"{self._sysobjectid_cache}.1.1.1.{info_suffix}"
        return self.snmp.get(legacy_oid)
    
    def get_firmware(self) -> Optional[str]:
        """
        Retrieve firmware/software version from the device.
        
        Tries the standard TP-Link MIB path first, then falls back to
        legacy path for older devices.
        
        Returns:
            Canonical firmware version string, or None if not found
        """
        sw_version = (self.snmp.get(self.TP_SYSINFO_SW_VERSION) or 
                     self._get_older_sys_info("6.0"))
        
        if not sw_version:
            return None
        
        return self._get_canonical_string(sw_version)
    
    def get_mac_address(self) -> Optional[str]:
        """
        Retrieve the device's MAC address.
        
        TP-Link devices may return MAC addresses with dash separators,
        which need to be converted to colon separators.
        
        Returns:
            Canonical MAC address (colon-separated), or None if not found
        """
        mac_addr = (self.snmp.get(self.TP_SYSINFO_MAC_ADDR) or 
                   self._get_older_sys_info("7.0"))
        
        if not mac_addr:
            return None
        
        mac_addr = self._get_canonical_string(mac_addr)
        # Convert dash separator to colon separator
        mac_addr = mac_addr.replace('-', ':')
        
        return self._get_canonical_mac_address(mac_addr)
    
    def get_model(self) -> Optional[str]:
        """
        Extract device model from hardware version string.
        
        Returns the first word of the hardware version, which typically
        contains the model identifier (e.g., "TL-SG108E" from 
        "TL-SG108E 1.0").
        
        Returns:
            Model identifier string, or None if not found or already set
        """
        # Don't overwrite existing model
        if self.device and self.device.get('MODEL'):
            return None
        
        hw_version = (self.snmp.get(self.TP_SYSINFO_HW_VERSION) or 
                     self._get_older_sys_info("5.0"))
        
        if not hw_version:
            return None
        
        hw_version = self._get_canonical_string(hw_version)
        
        # Extract first word as model
        match = re.match(r'^(\S+)', hw_version)
        if match:
            return match.group(1)
        
        return None
    
    def get_serial(self) -> Optional[str]:
        """
        Retrieve device serial number.
        
        For older TP-Link devices without a serial number OID, this may
        return the MAC address string with dash separators.
        
        Returns:
            Serial number string, or None if not found
        """
        serial = (self.snmp.get(self.TP_SYSINFO_SERIAL_NUM) or 
                 self._get_older_sys_info("7.0"))
        
        if not serial:
            return None
        
        return self._get_canonical_string(serial)
    
    def run(self) -> None:
        """
        Main execution method to gather and populate device inventory data.
        
        This method:
        1. Retrieves and adds hardware version firmware information
        2. Handles both modern and legacy TP-Link device paths
        3. Collects VLAN configuration and maps VLANs to ports
        4. Populates the device dictionary with all gathered information
        
        The method modifies self.device in-place, adding firmware entries
        and VLAN mappings to the appropriate port structures.
        """
        if not self.device:
            return
        
        # Try modern path for hardware version
        hardware_version = self._get_canonical_string(
            self.snmp.get(self.TP_SYSINFO_HW_VERSION)
        )
        
        if hardware_version and not self._is_empty(hardware_version):
            self._add_firmware({
                'NAME': self.device.get('MODEL'),
                'DESCRIPTION': 'TP-Link Hardware version',
                'TYPE': 'hardware',
                'VERSION': hardware_version,
                'MANUFACTURER': 'TP-Link'
            })
        
        # For older devices, try legacy path
        if self._sysobjectid_cache:
            hardware_version = self._get_older_sys_info("5.0")
            if hardware_version:
                self._add_firmware({
                    'NAME': self.device.get('MODEL'),
                    'DESCRIPTION': 'TP-Link Hardware version',
                    'TYPE': 'hardware',
                    'VERSION': self._get_canonical_string(hardware_version),
                    'MANUFACTURER': 'TP-Link'
                })
        
        # Process VLAN configuration
        vlan_port_number = self.snmp.walk(self.VLAN_PORT_NUMBER)
        
        if vlan_port_number:
            vlans = self._get_vlans()
            
            if vlans:
                # Map VLANs to ports
                for oid_suffix, port_value in vlan_port_number.items():
                    port = self._get_canonical_string(port_value)
                    
                    # Check if port exists in device structure and has VLAN data
                    ports_dict = self.device.get('PORTS', {}).get('PORT', {})
                    if (port in ports_dict and
                        port in vlans and
                        not ports_dict[port].get('VLANS')):
                        
                        # Initialize VLANS structure if needed
                        if 'VLANS' not in ports_dict[port]:
                            ports_dict[port]['VLANS'] = {}
                        
                        # Assign VLAN list to port
                        ports_dict[port]['VLANS']['VLAN'] = vlans[port]
    
    @staticmethod
    def _parse_ports_def(ports_def: str) -> List[str]:
        """
        Parse TP-Link port definition string into individual port identifiers.
        
        TP-Link uses a compact notation for port lists that can include:
        - Individual ports: "GigabitEthernet1/0/1"
        - Port ranges: "GigabitEthernet1/0/1-5" expands to 1,2,3,4,5
        - Comma-separated combinations: "Gi1/0/1-3,Gi1/0/5"
        
        Examples:
            "1,2,3" -> ["1", "2", "3"]
            "1-3" -> ["1", "2", "3"]
            "Gi1/0/1-3" -> ["Gi1/0/1", "Gi1/0/2", "Gi1/0/3"]
            "Gi1/0/1,Gi1/0/5-7" -> ["Gi1/0/1", "Gi1/0/5", "Gi1/0/6", "Gi1/0/7"]
        
        Args:
            ports_def: Port definition string from TP-Link device
            
        Returns:
            List of individual port identifiers
        """
        ports = []
        
        # Split on commas and process each definition
        for definition in ports_def.split(','):
            definition = definition.strip()
            
            if not definition:
                continue
            
            # Check for range notation: prefix + startnum-endnum
            match = re.match(r'^(\S*)(\d+)-(\d+)$', definition)
            
            if match:
                prefix, start, end = match.groups()
                start_num = int(start)
                end_num = int(end)
                
                # Only expand if end > start (valid range)
                if end_num > start_num:
                    ports.extend([f"{prefix}{num}" for num in range(start_num, end_num + 1)])
            else:
                # Single port, add as-is
                ports.append(definition)
        
        return ports
    
    def _get_vlans(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve and parse VLAN configuration from the device.
        
        This method walks the TP-Link VLAN MIB tables to construct a complete
        picture of VLAN configuration, including:
        - VLAN IDs and names/descriptions
        - Tagged port memberships
        - Untagged port memberships
        - Removed port memberships (for delta updates)
        
        The method handles TP-Link's specific VLAN representation where port
        memberships are specified as comma-separated lists or ranges.
        
        Returns:
            Dictionary mapping port identifiers to lists of VLAN configurations.
            Each VLAN config contains NUMBER, NAME, and TAGGED fields.
            
        Example:
            {
                'GigabitEthernet1/0/1': [
                    {'NUMBER': '100', 'NAME': 'Management', 'TAGGED': 1},
                    {'NUMBER': '200', 'NAME': 'Guest', 'TAGGED': 0}
                ],
                'GigabitEthernet1/0/2': [...]
            }
        """
        results = {}
        
        # Walk VLAN description and status tables
        dot1q_vlan_description = self.snmp.walk(self.DOT1Q_VLAN_DESCRIPTION)
        dot1q_vlan_status = self.snmp.walk(self.DOT1Q_VLAN_STATUS)
        
        if not (dot1q_vlan_description and dot1q_vlan_status):
            return results
        
        # Walk additional VLAN tables
        dot1q_vlan_id = self.snmp.walk(self.DOT1Q_VLAN_ID)
        vlan_tag_port_member = self.snmp.walk(self.VLAN_TAG_PORT_MEMBER_ADD)
        vlan_untag_port_member = self.snmp.walk(self.VLAN_UNTAG_PORT_MEMBER_ADD)
        vlan_port_member_remove = self.snmp.walk(self.VLAN_PORT_MEMBER_REMOVE)
        
        # Process each VLAN (sorted by OID suffix for consistency)
        for suffix in sorted(dot1q_vlan_status.keys()):
            # Only process active VLANs (status == 1)
            if dot1q_vlan_status[suffix] != '1':
                continue
            
            vlan_id = self._get_canonical_string(dot1q_vlan_id.get(suffix, ''))
            name = self._get_canonical_string(dot1q_vlan_description.get(suffix, ''))
            
            # Dictionary to accumulate port-VLAN associations
            # Structure: {port: {vlan_id: {...config...}}}
            ports = {}
            
            # Process tagged ports
            tagged_def = self._get_canonical_string(
                vlan_tag_port_member.get(suffix, '')
            )
            
            if tagged_def and not self._is_empty(tagged_def):
                for port in self._parse_ports_def(tagged_def):
                    if port not in ports:
                        ports[port] = {}
                    ports[port][vlan_id] = {
                        'NUMBER': vlan_id,
                        'NAME': name if name else '',
                        'TAGGED': 1
                    }
            
            # Process untagged ports
            untagged_def = self._get_canonical_string(
                vlan_untag_port_member.get(suffix, '')
            )
            
            if untagged_def and not self._is_empty(untagged_def):
                for port in self._parse_ports_def(untagged_def):
                    if port not in ports:
                        ports[port] = {}
                    ports[port][vlan_id] = {
                        'NUMBER': vlan_id,
                        'NAME': name if name else '',
                        'TAGGED': 0
                    }
            
            # Process removed ports (remove from membership)
            remove_def = self._get_canonical_string(
                vlan_port_member_remove.get(suffix, '')
            )
            
            if remove_def and not self._is_empty(remove_def):
                for port in self._parse_ports_def(remove_def):
                    if port in ports and vlan_id in ports[port]:
                        del ports[port][vlan_id]
            
            # Consolidate results: convert per-VLAN port dict to final structure
            for port, vlan_configs in ports.items():
                if port not in results:
                    results[port] = []
                
                # Sort VLANs by number and add to results
                sorted_vlans = sorted(
                    vlan_configs.values(),
                    key=lambda x: int(x['NUMBER'])
                )
                results[port].extend(sorted_vlans)
        
        return results
    
    @staticmethod
    def _get_canonical_string(value: Any) -> str:
        """
        Convert SNMP value to canonical string representation.
        
        Handles various input types and cleans up the string:
        - Strips leading/trailing whitespace
        - Converts None to empty string
        - Handles numeric types
        
        Args:
            value: Value to canonicalize
            
        Returns:
            Canonical string representation
        """
        if value is None:
            return ''
        
        return str(value).strip()
    
    @staticmethod
    def _get_canonical_mac_address(mac: str) -> str:
        """
        Convert MAC address to canonical format.
        
        Ensures MAC address is in standard format:
        - Uppercase hex digits
        - Colon-separated octets
        - Properly padded (e.g., 0A not A)
        
        Args:
            mac: MAC address in various formats
            
        Returns:
            Canonical MAC address (XX:XX:XX:XX:XX:XX)
        """
        # Remove common separators
        mac_clean = mac.replace(':', '').replace('-', '').replace('.', '')
        
        # Ensure we have 12 hex digits
        if len(mac_clean) != 12:
            return mac  # Return as-is if invalid
        
        # Format as XX:XX:XX:XX:XX:XX
        octets = [mac_clean[i:i+2] for i in range(0, 12, 2)]
        return ':'.join(octets).upper()
    
    @staticmethod
    def _is_empty(value: Any) -> bool:
        """
        Check if a value is empty or None.
        
        Args:
            value: Value to check
            
        Returns:
            True if value is None, empty string, or whitespace only
        """
        if value is None:
            return True
        
        if isinstance(value, str):
            return not value.strip()
        
        return False
    
    def _add_firmware(self, firmware_info: Dict[str, str]) -> None:
        """
        Add firmware/hardware information to device inventory.
        
        Args:
            firmware_info: Dictionary containing firmware details
                          (NAME, DESCRIPTION, TYPE, VERSION, MANUFACTURER)
        """
        if 'FIRMWARE' not in self.device:
            self.device['FIRMWARE'] = []
        
        self.device['FIRMWARE'].append(firmware_info)


# Example usage and testing
if __name__ == "__main__":
    # Mock SNMP client for demonstration
    class MockSNMP:
        def __init__(self, data):
            self.data = data
        
        def get(self, oid):
            return self.data.get(oid)
        
        def walk(self, oid):
            results = {}
            for key, value in self.data.items():
                if key.startswith(oid):
                    suffix = key[len(oid):]
                    if suffix:
                        results[suffix] = value
            return results if results else None
    
    # Sample data
    mock_data = {
        '.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.11863.1.1.1',
        '.1.3.6.1.4.1.11863.6.1.1.5.0': 'TL-SG108E 1.0',
        '.1.3.6.1.4.1.11863.6.1.1.6.0': '1.0.0 Build 20200101 Rel.50000',
        '.1.3.6.1.4.1.11863.6.1.1.7.0': '00-11-22-33-44-55',
        '.1.3.6.1.4.1.11863.6.1.1.8.0': 'SN123456789',
    }
    
    snmp_client = MockSNMP(mock_data)
    device = {'MODEL': None, 'PORTS': {'PORT': {}}}
    
    tplink = TpLinkMibSupport(snmp_client, device)
    
    print("TP-Link Device Information:")
    print(f"Model: {tplink.get_model()}")
    print(f"Firmware: {tplink.get_firmware()}")
    print(f"MAC Address: {tplink.get_mac_address()}")
    print(f"Serial: {tplink.get_serial()}")
    
    # Test port parsing
    print("\nPort Parsing Tests:")
    test_cases = [
        "1,2,3",
        "1-5",
        "Gi1/0/1-3",
        "Gi1/0/1,Gi1/0/5-7",
        "GigabitEthernet1/0/1-2,GigabitEthernet1/0/10"
    ]
    
    for test in test_cases:
        parsed = TpLinkMibSupport._parse_ports_def(test)
        print(f"  '{test}' -> {parsed}")
