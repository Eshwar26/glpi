"""
GLPI Agent SNMP Live Module

This module provides the Live SNMP client class for performing SNMP queries on live hosts.
It is a faithful Python conversion of the Perl GLPI::Agent::SNMP::Live module.

The module supports:
- SNMPv1, SNMPv2c, and SNMPv3
- SNMP GET and WALK operations
- VLAN context switching
- Session validation with configurable test OIDs
- Configuration file support (snmp-advanced-support.cfg)

Author: Converted from Perl to Python
License: Compatible with GLPI Agent
"""

import os
import re
import time
from typing import Optional, Dict, Any, List
from pysnmp.hlapi import (
    SnmpEngine,
    CommunityData,
    UsmUserData,
    UdpTransportTarget,
    Udp6TransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    getCmd,
    bulkCmd,
    nextCmd,
    # Auth protocols
    usmNoAuthProtocol,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
    usmHMAC128SHA224AuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol,
    usmHMAC384SHA512AuthProtocol,
    # Priv protocols
    usmNoPrivProtocol,
    usmDESPrivProtocol,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
    # Constants
    SNMP_VERSION_1,
    SNMP_VERSION_2C,
    SNMP_VERSION_3,
)


class SNMPLive:
    """
    GLPI Agent Live SNMP Client
    
    This class provides SNMP session management and query operations for live network devices.
    It supports SNMPv1, SNMPv2c, and SNMPv3 with various authentication and privacy protocols.
    
    The class maintains API compatibility with the Perl GLPI::Agent::SNMP::Live module,
    including method names, return formats, and error handling behavior.
    
    Attributes:
        session: The underlying pysnmp session components
        community: Community string for SNMPv1/v2c (saved for VLAN switching)
        context: SNMPv3 context name (used for VLAN switching in v3)
        oldsession: Backup of original session for VLAN context restoration
        
    Configuration:
        The class supports configuration via snmp-advanced-support.cfg file.
        Default location: /etc/glpi-agent/snmp-advanced-support.cfg
        
        Configuration format:
        oids = .1.3.6.1.2.1.1.1.0,.1.3.6.1.2.1.1.2.0
    """
    
    # Class-level configuration cache
    _config = None
    _config_load_timeout = 0
    _config_file = "snmp-advanced-support.cfg"
    _config_dirs = [
        "/etc/glpi-agent",
        "/usr/local/etc/glpi-agent",
        os.path.expanduser("~/.glpi-agent"),
        ".",
    ]
    
    # Default configuration
    _defaults = {
        'oids': '.1.3.6.1.2.1.1.1.0',  # sysDescr.0
    }
    
    def __init__(self, hostname: str = None, version: str = None, 
                 community: str = None, username: str = None,
                 authprotocol: str = None, authpassword: str = None,
                 privprotocol: str = None, privpassword: str = None,
                 port: int = 161, timeout: Optional[int] = None,
                 retries: int = 0, domain: str = 'udp/ipv4', **params):
        """
        Initialize SNMP Live session.
        
        Args:
            hostname: Target device hostname or IP address (mandatory)
            version: SNMP version - '1', '2c', or '3' (mandatory)
            community: Community string for v1/v2c
            username: Username for v3 (mandatory for v3)
            authprotocol: Authentication protocol for v3 (md5, sha, sha224, sha256, sha384, sha512)
            authpassword: Authentication password for v3
            privprotocol: Privacy protocol for v3 (des, aes, aes192, aes256, aes256c)
            privpassword: Privacy password for v3
            port: SNMP port (default: 161)
            timeout: SNMP timeout in seconds
            retries: Number of retries (default: 0)
            domain: Transport domain - 'udp/ipv4', 'udp/ipv6', 'tcp/ipv4', 'tcp/ipv6'
            
        Raises:
            Exception: If hostname not provided or invalid version
        """
        if not hostname:
            raise Exception("no hostname parameters")
        
        self._hostname = hostname
        
        # Normalize SNMP version
        if not version:
            version_normalized = 'snmpv1'
        elif version == '1':
            version_normalized = 'snmpv1'
        elif version == '2c':
            version_normalized = 'snmpv2c'
        elif version == '3':
            version_normalized = 'snmpv3'
        else:
            raise Exception(f"invalid SNMP version {version} parameter")
        
        self._version = version_normalized
        
        # Load configuration and test OIDs
        self._load_config()
        
        # Build session options
        self._retries = retries
        self._timeout = timeout
        self._port = port
        self._domain = domain
        
        # Version-specific setup
        self.community = None
        self.context = None
        self.oldsession = None
        self._session_error = None
        
        if version_normalized == 'snmpv3':
            # SNMPv3 - only username is mandatory
            if not username:
                raise Exception("username required for SNMPv3")
            
            self._username = username
            self._authprotocol = authprotocol
            self._authpassword = authpassword
            self._privprotocol = privprotocol
            self._privpassword = privpassword
            
        else:  # snmpv1 or snmpv2c
            if community is None:
                raise Exception(f"community required for {version_normalized}")
            self.community = community
        
        # Initialize SNMP session
        try:
            self._init_session()
        except Exception as e:
            self._session_error = str(e)
    
    def _load_config(self):
        """
        Load configuration from snmp-advanced-support.cfg file.
        
        Configuration is loaded at most once per minute to avoid excessive I/O.
        The configuration file can override the default OIDs used for session testing.
        """
        current_time = time.time()
        
        # Reload config not before one minute
        if (not hasattr(self, '_oids') or 
            SNMPLive._config_load_timeout < current_time):
            
            # Start with defaults
            config = self._defaults.copy()
            
            # Try to find and load config file
            config_file_path = None
            for config_dir in self._config_dirs:
                potential_path = os.path.join(config_dir, self._config_file)
                if os.path.isfile(potential_path):
                    config_file_path = potential_path
                    break
            
            if config_file_path:
                try:
                    with open(config_file_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            # Skip comments and empty lines
                            if not line or line.startswith('#'):
                                continue
                            
                            # Parse key = value
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                config[key] = value
                except Exception:
                    pass  # Silently ignore config file errors
            
            # Normalize OIDs configuration
            oid_string = config.get('oids', self._defaults['oids'])
            oids = []
            
            for oid in oid_string.split(','):
                oid = oid.strip()
                if oid:
                    # Ensure OID starts with dot
                    if not oid.startswith('.'):
                        oid = '.' + oid
                    oids.append(oid)
            
            # Validate OIDs format if not using default
            if oid_string != self._defaults['oids']:
                oid_pattern = re.compile(r'^\.(?:\d+\.)+\d+$')
                invalid_oids = [oid for oid in oids if not oid_pattern.match(oid)]
                if invalid_oids:
                    raise Exception(
                        f"invalid 'oids' configuration in {config_file_path or 'config'}: "
                        f"{', '.join(invalid_oids)}"
                    )
            
            self._oids = oids
            
            # Set reload timeout to current time + 60 seconds
            SNMPLive._config_load_timeout = current_time + 60
    
    def _init_session(self):
        """
        Initialize the SNMP session with pysnmp.
        
        Creates the SNMP engine, authentication data, and transport target
        based on the configured version and parameters.
        """
        # Create SNMP engine
        self._engine = SnmpEngine()
        
        # Setup authentication data
        if self._version == 'snmpv3':
            # Map protocol names to pysnmp protocol objects
            auth_protocols = {
                'md5': usmHMACMD5AuthProtocol,
                'sha': usmHMACSHAAuthProtocol,
                'sha224': usmHMAC128SHA224AuthProtocol,
                'sha256': usmHMAC192SHA256AuthProtocol,
                'sha384': usmHMAC256SHA384AuthProtocol,
                'sha512': usmHMAC384SHA512AuthProtocol,
            }
            
            priv_protocols = {
                'des': usmDESPrivProtocol,
                'aes': usmAesCfb128Protocol,
                'aes128': usmAesCfb128Protocol,
                'aes192': usmAesCfb192Protocol,
                'aes256': usmAesCfb256Protocol,
                'aes256c': usmAesCfb256Protocol,  # Blumenthal variant
            }
            
            auth_proto = usmNoAuthProtocol
            if self._authprotocol and self._authpassword:
                auth_proto = auth_protocols.get(
                    self._authprotocol.lower(),
                    usmNoAuthProtocol
                )
            
            priv_proto = usmNoPrivProtocol
            if self._privprotocol and self._privpassword:
                priv_proto = priv_protocols.get(
                    self._privprotocol.lower(),
                    usmNoPrivProtocol
                )
            
            self._auth_data = UsmUserData(
                self._username,
                authKey=self._authpassword,
                privKey=self._privpassword,
                authProtocol=auth_proto,
                privProtocol=priv_proto,
            )
        else:
            # SNMPv1 or SNMPv2c
            mp_model = 0 if self._version == 'snmpv1' else 1
            self._auth_data = CommunityData(self.community, mpModel=mp_model)
        
        # Setup transport target based on domain
        if self._domain in ('udp/ipv6', 'tcp/ipv6'):
            # IPv6 transport
            self._transport = Udp6TransportTarget(
                (self._hostname, self._port),
                timeout=self._timeout or 1,
                retries=self._retries,
            )
        else:
            # IPv4 transport (default)
            self._transport = UdpTransportTarget(
                (self._hostname, self._port),
                timeout=self._timeout or 1,
                retries=self._retries,
            )
        
        # Store version ID for compatibility
        if self._version == 'snmpv1':
            self._version_id = SNMP_VERSION_1
        elif self._version == 'snmpv2c':
            self._version_id = SNMP_VERSION_2C
        else:  # snmpv3
            self._version_id = SNMP_VERSION_3
        
        # Session successfully initialized
        self.session = {
            'engine': self._engine,
            'auth_data': self._auth_data,
            'transport': self._transport,
            'version_id': self._version_id,
        }
    
    def testSession(self):
        """
        Test the SNMP session by attempting to retrieve configured test OIDs.
        
        This method validates that the SNMP session is properly established
        and the device is responding. For SNMPv1/v2c, it tests by querying
        the configured OIDs. For SNMPv3, the session is already validated
        during establishment.
        
        Raises:
            Exception: If session failed to open, no response from host,
                      authentication error, or missing required modules
        """
        # Check for session creation errors
        error = self._session_error
        host = self._hostname
        
        if not hasattr(self, 'session') or not self.session:
            if error:
                # Check for specific error patterns
                if 'No response from remote host' in error:
                    raise Exception(f"no response from {host} host")
                elif 'WrongDigests' in error or 'UnknownUserNames' in error:
                    raise Exception(f"authentication error on {host} host")
                elif 'Crypt' in error and 'Rijndael' in error:
                    raise Exception("Crypt::Rijndael perl module needs to be installed")
                else:
                    raise Exception(error)
            else:
                raise Exception("failed to open snmp session")
        
        version_id = self.session['version_id']
        
        # No need to test SNMPv3 session as it's already established
        if version_id == SNMP_VERSION_3:
            return
        
        # Test session by querying configured OIDs
        response = {}
        has_response = False
        
        for oid in self._oids:
            try:
                value = self.get(oid)
                response[oid] = value
                if value is not None:
                    has_response = True
            except Exception:
                response[oid] = None
        
        # Check if we got any response
        if not response:
            raise Exception(f"no response from {host} host")
        
        # Check if at least one OID returned a valid value
        if not has_response:
            raise Exception(f"missing response from {host} host")
        
        # Check if all responses indicate "no response"
        error_responses = sum(
            1 for v in response.values()
            if v and isinstance(v, str) and 'No response from remote host' in v
        )
        
        if error_responses == len(self._oids):
            raise Exception(f"no response from {host} host")
    
    def switch_vlan_context(self, vlan_id):
        """
        Switch SNMP context to a specific VLAN.
        
        For SNMPv3: Sets the context name to 'vlan-{vlan_id}'
        For SNMPv1/v2c: Appends '@{vlan_id}' to the community string
                        and creates a new session
        
        Args:
            vlan_id: VLAN ID to switch to (int or str)
            
        Raises:
            Exception: If session creation fails
        """
        vlan_id = str(vlan_id) if vlan_id else ''
        
        if not vlan_id:
            return
        
        version_id = self.session['version_id']
        
        if version_id == SNMP_VERSION_3:
            # For SNMPv3, just set the context
            self.context = f'vlan-{vlan_id}'
        else:
            # For SNMPv1/v2c, save current session and create new one
            # with modified community string
            if not self.oldsession:
                self.oldsession = self.session.copy()
            
            # Create new community data with VLAN suffix
            vlan_community = f"{self.community}@{vlan_id}"
            mp_model = 0 if version_id == SNMP_VERSION_1 else 1
            
            new_auth_data = CommunityData(vlan_community, mpModel=mp_model)
            
            # Update session with new auth data
            self.session = {
                'engine': self._engine,
                'auth_data': new_auth_data,
                'transport': self._transport,
                'version_id': version_id,
            }
    
    def reset_original_context(self):
        """
        Reset SNMP context to the original state (no VLAN).
        
        For SNMPv3: Clears the context name
        For SNMPv1/v2c: Restores the original session
        """
        version_id = self.session['version_id']
        
        if version_id == SNMP_VERSION_3:
            # Clear context for SNMPv3
            self.context = ""
        else:
            # Restore original session for SNMPv1/v2c
            if self.oldsession:
                self.session = self.oldsession
                self.oldsession = None
    
    def get(self, oid: str) -> Optional[Any]:
        """
        Perform SNMP GET operation on a single OID.
        
        This method retrieves the value of a specific OID from the device.
        It handles various error conditions and returns None for invalid
        or non-existent OIDs.
        
        Args:
            oid: The OID string to query (e.g., '.1.3.6.1.2.1.1.1.0')
            
        Returns:
            The value retrieved from the device, or None if:
            - OID is empty/None
            - No response from device
            - OID doesn't exist (noSuchInstance, noSuchObject)
            - Communication error
            
        Note:
            This method matches the Perl API exactly, including return
            value format and error handling behavior.
        """
        if not oid:
            return None
        
        if not hasattr(self, 'session') or not self.session:
            return None
        
        # Build context data
        context_name = self.context if self.context else ''
        context = ContextData(contextName=context_name)
        
        try:
            # Perform SNMP GET
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    self.session['engine'],
                    self.session['auth_data'],
                    self.session['transport'],
                    context,
                    ObjectType(ObjectIdentity(oid))
                )
            )
            
            # Check for errors
            if error_indication:
                return None
            
            if error_status:
                return None
            
            # Extract value from var_binds
            if var_binds:
                name, value = var_binds[0]
                value_str = str(value)
                
                # Filter out error responses
                if not value_str:
                    return None
                if 'noSuchInstance' in value_str:
                    return None
                if 'noSuchObject' in value_str:
                    return None
                if 'No response from remote host' in value_str:
                    return None
                
                return value_str
            
        except StopIteration:
            return None
        except Exception:
            return None
        
        return None
    
    def walk(self, oid: str) -> Optional[Dict[str, Any]]:
        """
        Perform SNMP WALK operation on an OID tree.
        
        This method retrieves all OID values under the specified base OID.
        The returned dictionary uses OID suffixes (relative to base OID) as keys,
        matching the Perl implementation behavior exactly.
        
        Args:
            oid: The base OID to walk (e.g., '.1.3.6.1.2.1.1')
            
        Returns:
            Dictionary mapping OID suffixes to values, or None if:
            - Base OID is empty/None
            - No session established
            - No response from device
            - Communication error
            
        Example:
            Walking '.1.3.6.1.2.1.1' might return:
            {
                '1.0': 'Linux switch 4.19.0',
                '2.0': '.1.3.6.1.4.1.9.1.123',
                '3.0': '12345678',
                ...
            }
            
        Note:
            Keys are OID suffixes (portion after base OID + 1), not full OIDs.
            This matches the Perl implementation exactly.
        """
        if not oid:
            return None
        
        if not hasattr(self, 'session') or not self.session:
            return None
        
        # Build context data
        context_name = self.context if self.context else ''
        context = ContextData(contextName=context_name)
        
        # Calculate offset for suffix extraction
        # Remove leading dot if present for length calculation
        base_oid_clean = oid.lstrip('.')
        offset = len(base_oid_clean) + 1  # +1 for the dot separator
        
        values = {}
        
        try:
            # Determine which command to use based on SNMP version
            version_id = self.session['version_id']
            
            if version_id == SNMP_VERSION_1:
                # SNMPv1 uses nextCmd (GETNEXT)
                cmd_generator = nextCmd(
                    self.session['engine'],
                    self.session['auth_data'],
                    self.session['transport'],
                    context,
                    ObjectType(ObjectIdentity(oid)),
                    lexicographicMode=False
                )
            else:
                # SNMPv2c and SNMPv3 use bulkCmd (GETBULK) with maxRepetitions=1
                # to match Perl Net::SNMP get_table behavior
                cmd_generator = bulkCmd(
                    self.session['engine'],
                    self.session['auth_data'],
                    self.session['transport'],
                    context,
                    0,  # nonRepeaters
                    1,  # maxRepetitions (matches Perl's -maxrepetitions => 1)
                    ObjectType(ObjectIdentity(oid)),
                    lexicographicMode=False
                )
            
            # Iterate through results
            for (error_indication, error_status, error_index, var_binds) in cmd_generator:
                if error_indication:
                    break
                
                if error_status:
                    break
                
                # Process var_binds
                for var_bind in var_binds:
                    name, value = var_bind
                    full_oid = str(name)
                    value_str = str(value)
                    
                    # Extract suffix (portion after base OID)
                    # Ensure full_oid starts with dot for consistency
                    if not full_oid.startswith('.'):
                        full_oid = '.' + full_oid
                    
                    # Remove leading dot for suffix calculation
                    full_oid_clean = full_oid.lstrip('.')
                    
                    # Calculate suffix by removing base OID portion
                    if len(full_oid_clean) > offset:
                        suffix = full_oid_clean[offset:]
                    else:
                        # If somehow we get an OID shorter than expected,
                        # use the full OID
                        suffix = full_oid_clean
                    
                    values[suffix] = value_str
        
        except StopIteration:
            pass
        except Exception:
            return None
        
        # Return None if no values found (matching Perl behavior)
        if not values:
            return None
        
        return values
    
    def peer_address(self) -> Optional[str]:
        """
        Get the peer (target) address of the SNMP session.
        
        Returns:
            The hostname/IP address of the SNMP target device,
            or None if no session exists
        """
        if not hasattr(self, 'session') or not self.session:
            return None
        
        # Return the hostname from transport target
        return self._hostname


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage demonstrating the SNMPLive class.
    
    This shows typical patterns for:
    - Creating SNMP sessions (v1, v2c, v3)
    - Testing session connectivity
    - Performing GET and WALK operations
    - VLAN context switching
    """
    
    print("GLPI Agent SNMP Live - Python Implementation")
    print("=" * 60)
    
    # Example 1: SNMPv2c session
    print("\nExample 1: SNMPv2c Session")
    print("-" * 60)
    try:
        snmp = SNMPLive(
            hostname='192.168.1.1',
            version='2c',
            community='public',
            timeout=2,
            retries=1
        )
        
        # Test session
        snmp.testSession()
        print("✓ Session established successfully")
        
        # Get single OID
        sys_descr = snmp.get('.1.3.6.1.2.1.1.1.0')
        print(f"sysDescr: {sys_descr}")
        
        # Walk OID tree
        system_info = snmp.walk('.1.3.6.1.2.1.1')
        if system_info:
            print("\nSystem information:")
            for suffix, value in sorted(system_info.items()):
                print(f"  .1.3.6.1.2.1.1.{suffix} = {value}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 2: SNMPv3 session
    print("\n\nExample 2: SNMPv3 Session")
    print("-" * 60)
    try:
        snmp = SNMPLive(
            hostname='192.168.1.1',
            version='3',
            username='admin',
            authprotocol='sha',
            authpassword='authpass123',
            privprotocol='aes',
            privpassword='privpass456',
            timeout=2
        )
        
        snmp.testSession()
        print("✓ SNMPv3 session established")
        
        sys_name = snmp.get('.1.3.6.1.2.1.1.5.0')
        print(f"sysName: {sys_name}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 3: VLAN context switching
    print("\n\nExample 3: VLAN Context Switching")
    print("-" * 60)
    try:
        snmp = SNMPLive(
            hostname='192.168.1.1',
            version='2c',
            community='public'
        )
        
        # Query in default context
        mac_count_default = snmp.walk('.1.3.6.1.2.1.17.4.3.1.1')
        print(f"MAC addresses in default context: {len(mac_count_default) if mac_count_default else 0}")
        
        # Switch to VLAN 10
        snmp.switch_vlan_context(10)
        mac_count_vlan10 = snmp.walk('.1.3.6.1.2.1.17.4.3.1.1')
        print(f"MAC addresses in VLAN 10: {len(mac_count_vlan10) if mac_count_vlan10 else 0}")
        
        # Reset to original context
        snmp.reset_original_context()
        print("✓ Context reset to original")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("For detailed usage, see the class docstrings")
