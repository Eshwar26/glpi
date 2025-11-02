"""
SNMPv3 User-based Security Model (USM) Implementation

This module implements the SNMPv3 User-based Security Model as defined in:
- RFC 3414: User-based Security Model (USM) for version 3 of SNMP
- RFC 3826: The Advanced Encryption Standard (AES) Cipher Algorithm in the SNMP USM
- Draft extensions for SHA-2 family and additional AES modes

The USM provides SNMP message level security, implementing:
1. Data integrity (authentication using HMAC)
2. Data origin authentication (via shared secrets)
3. Data confidentiality (encryption using DES, 3DES, or AES)
4. Protection against message replay, delay, and redirection

Copyright: Ported from Net::SNMP::Security::USM by David M. Town
License: Same terms as Python itself
"""

import time
import struct
import hashlib
import hmac
from typing import Optional, Dict, Tuple, Any, Union, List
from dataclasses import dataclass
from enum import Enum

# Cryptographic imports
try:
    from Crypto.Cipher import DES, DES3, AES
    from Crypto.Util import Counter
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: PyCryptodome not available. Install with: pip install pycryptodome")


# ============================================================================
# Constants and Protocol Definitions
# ============================================================================

# SNMP Version
SNMP_VERSION_1 = 0
SNMP_VERSION_2C = 1
SNMP_VERSION_3 = 3

# Module version
VERSION = "4.0.1"

# Boolean constants
TRUE = True
FALSE = False


# ============================================================================
# Security Levels (RFC 3414 Section 3.4)
# ============================================================================

class SecurityLevel(Enum):
    """
    SNMPv3 Security Levels
    
    - NOAUTHNOPRIV: No authentication, no privacy (equivalent to SNMPv1/v2c)
    - AUTHNOPRIV: Authentication without privacy (integrity only)
    - AUTHPRIV: Authentication with privacy (integrity + confidentiality)
    """
    NOAUTHNOPRIV = 1  # No authentication or encryption
    AUTHNOPRIV = 2    # Authentication without encryption  
    AUTHPRIV = 3      # Authentication with encryption

SECURITY_LEVEL_NOAUTHNOPRIV = SecurityLevel.NOAUTHNOPRIV
SECURITY_LEVEL_AUTHNOPRIV = SecurityLevel.AUTHNOPRIV
SECURITY_LEVEL_AUTHPRIV = SecurityLevel.AUTHPRIV


# ============================================================================
# Security Models (RFC 3411 Section 3.1.3)
# ============================================================================

class SecurityModel(Enum):
    """SNMPv3 Security Models"""
    ANY = 0      # Reserved for any
    SNMPV1 = 1   # SNMPv1
    SNMPV2C = 2  # SNMPv2c
    USM = 3      # User-based Security Model

SECURITY_MODEL_ANY = SecurityModel.ANY
SECURITY_MODEL_SNMPV1 = SecurityModel.SNMPV1
SECURITY_MODEL_SNMPV2C = SecurityModel.SNMPV2C
SECURITY_MODEL_USM = SecurityModel.USM


# ============================================================================
# Authentication Protocols (RFC 3414 Section 6)
# ============================================================================

# OID definitions for authentication protocols
AUTH_PROTOCOL_NONE = '1.3.6.1.6.3.10.1.1.1'        # usmNoAuthProtocol
AUTH_PROTOCOL_HMACMD5 = '1.3.6.1.6.3.10.1.1.2'     # usmHMACMD5AuthProtocol
AUTH_PROTOCOL_HMACSHA = '1.3.6.1.6.3.10.1.1.3'     # usmHMACSHAAuthProtocol
AUTH_PROTOCOL_HMACSHA224 = '1.3.6.1.6.3.10.1.1.4'  # usmHMAC128SHA224AuthProtocol
AUTH_PROTOCOL_HMACSHA256 = '1.3.6.1.6.3.10.1.1.5'  # usmHMAC192SHA256AuthProtocol
AUTH_PROTOCOL_HMACSHA384 = '1.3.6.1.6.3.10.1.1.6'  # usmHMAC256SHA384AuthProtocol
AUTH_PROTOCOL_HMACSHA512 = '1.3.6.1.6.3.10.1.1.7'  # usmHMAC384SHA512AuthProtocol


# ============================================================================
# Privacy Protocols (RFC 3414 Section 7, RFC 3826)
# ============================================================================

# Standard privacy protocols
PRIV_PROTOCOL_NONE = '1.3.6.1.6.3.10.1.2.1'        # usmNoPrivProtocol
PRIV_PROTOCOL_DES = '1.3.6.1.6.3.10.1.2.2'         # usmDESPrivProtocol
PRIV_PROTOCOL_AESCFB128 = '1.3.6.1.6.3.10.1.2.4'   # usmAesCfb128Protocol (RFC 3826)

# Draft/Extended protocols
PRIV_PROTOCOL_DRAFT_3DESEDE = '1.3.6.1.4.1.14832.1.1'    # usm3DESPrivProtocol
PRIV_PROTOCOL_DRAFT_AESCFB128 = '1.3.6.1.4.1.14832.1.2'  # usmAESCfb128PrivProtocol
PRIV_PROTOCOL_DRAFT_AESCFB192 = '1.3.6.1.4.1.14832.1.3'  # usmAESCfb192PrivProtocol
PRIV_PROTOCOL_DRAFT_AESCFB256 = '1.3.6.1.4.1.14832.1.4'  # usmAESCfb256PrivProtocol

# Cisco-specific protocols
PRIV_PROTOCOL_AESCFB192_CISCO = '1.3.6.1.4.1.9.12.6.1.1'  # cusmAESCfb192PrivProtocol
PRIV_PROTOCOL_AESCFB256_CISCO = '1.3.6.1.4.1.9.12.6.1.2'  # cusmAESCfb256PrivProtocol


# ============================================================================
# Authentication Protocol Metadata
# ============================================================================

AUTH_PROTOCOL_INFO = {
    AUTH_PROTOCOL_NONE: {
        'name': 'None',
        'digest_length': 0,
        'mac_length': 0,
        'key_length': 0,
    },
    AUTH_PROTOCOL_HMACMD5: {
        'name': 'HMAC-MD5-96',
        'digest_length': 16,  # MD5 produces 128 bits (16 bytes)
        'mac_length': 12,     # Truncated to 96 bits (12 bytes) per RFC 3414
        'key_length': 16,
        'hash_func': hashlib.md5,
    },
    AUTH_PROTOCOL_HMACSHA: {
        'name': 'HMAC-SHA-96',
        'digest_length': 20,  # SHA-1 produces 160 bits (20 bytes)
        'mac_length': 12,     # Truncated to 96 bits (12 bytes) per RFC 3414
        'key_length': 20,
        'hash_func': hashlib.sha1,
    },
    AUTH_PROTOCOL_HMACSHA224: {
        'name': 'HMAC-SHA-224-128',
        'digest_length': 28,  # SHA-224 produces 224 bits (28 bytes)
        'mac_length': 16,     # Truncated to 128 bits (16 bytes)
        'key_length': 28,
        'hash_func': hashlib.sha224,
    },
    AUTH_PROTOCOL_HMACSHA256: {
        'name': 'HMAC-SHA-256-192',
        'digest_length': 32,  # SHA-256 produces 256 bits (32 bytes)
        'mac_length': 24,     # Truncated to 192 bits (24 bytes)
        'key_length': 32,
        'hash_func': hashlib.sha256,
    },
    AUTH_PROTOCOL_HMACSHA384: {
        'name': 'HMAC-SHA-384-256',
        'digest_length': 48,  # SHA-384 produces 384 bits (48 bytes)
        'mac_length': 32,     # Truncated to 256 bits (32 bytes)
        'key_length': 48,
        'hash_func': hashlib.sha384,
    },
    AUTH_PROTOCOL_HMACSHA512: {
        'name': 'HMAC-SHA-512-384',
        'digest_length': 64,  # SHA-512 produces 512 bits (64 bytes)
        'mac_length': 48,     # Truncated to 384 bits (48 bytes)
        'key_length': 64,
        'hash_func': hashlib.sha512,
    },
}


# ============================================================================
# Privacy Protocol Metadata
# ============================================================================

PRIV_PROTOCOL_INFO = {
    PRIV_PROTOCOL_NONE: {
        'name': 'None',
        'key_length': 0,
    },
    PRIV_PROTOCOL_DES: {
        'name': 'CBC-DES',
        'key_length': 16,  # RFC 3414 Section 8.2.1
        'cipher': 'DES',
    },
    PRIV_PROTOCOL_DRAFT_3DESEDE: {
        'name': 'CBC-3DES-EDE',
        'key_length': 32,  # Draft 3DES for USM Section 5.2.1
        'cipher': '3DES',
    },
    PRIV_PROTOCOL_AESCFB128: {
        'name': 'CFB128-AES-128',
        'key_length': 16,  # RFC 3826 Section 3.2.1
        'cipher': 'AES128',
    },
    PRIV_PROTOCOL_DRAFT_AESCFB192: {
        'name': 'CFB128-AES-192',
        'key_length': 24,  # Draft AES in the USM Section 3.2.1
        'cipher': 'AES192',
    },
    PRIV_PROTOCOL_DRAFT_AESCFB256: {
        'name': 'CFB128-AES-256',
        'key_length': 32,  # Draft AES in the USM Section 3.2.1
        'cipher': 'AES256',
    },
    PRIV_PROTOCOL_AESCFB192_CISCO: {
        'name': 'CFB128-AES-192c',
        'key_length': 24,
        'cipher': 'AES192',
    },
    PRIV_PROTOCOL_AESCFB256_CISCO: {
        'name': 'CFB128-AES-256c',
        'key_length': 32,
        'cipher': 'AES256',
    },
}


# ============================================================================
# Main USM Security Class
# ============================================================================

class USMSecurityError(Exception):
    """Exception raised for USM security-related errors"""
    pass


@dataclass
class SecurityParameters:
    """
    SNMP USM Security Parameters (RFC 3414 Section 2.4)
    
    These parameters are included in every SNMPv3 message using USM.
    """
    engine_id: bytes                    # Authoritative snmpEngineID
    engine_boots: int                   # snmpEngineBoots counter
    engine_time: int                    # snmpEngineTime in seconds
    user_name: str                      # Security name (username)
    auth_parameters: bytes              # Authentication parameters (MAC)
    priv_parameters: bytes              # Privacy parameters (salt/IV)


class USM:
    """
    User-based Security Model (USM) for SNMPv3
    
    This class implements the SNMPv3 User-based Security Model which provides:
    
    1. **Data Integrity**: Using HMAC with various hash algorithms
    2. **Data Origin Authentication**: Through shared secret keys
    3. **Data Confidentiality**: Using DES, 3DES, or AES encryption
    4. **Timeliness**: Protection against message replay and delay
    
    Key Concepts:
    
    **Engine ID**: Unique identifier for an SNMP engine (agent or manager).
    The authoritative engine ID is used in key localization.
    
    **Engine Boots**: Counter incremented each time the SNMP engine reinitializes.
    Used for replay protection.
    
    **Engine Time**: Seconds since last boot. Combined with boots for timeliness.
    
    **Security Levels**:
    - noAuthNoPriv: No security (like SNMPv1/v2c)
    - authNoPriv: Authentication only (integrity checking)
    - authPriv: Authentication + encryption (full security)
    
    **Key Derivation**: Keys are derived from passwords using a computationally
    expensive function (1 million MD5/SHA operations), then localized to the
    authoritative engine ID. This prevents offline dictionary attacks and
    ensures keys are unique per engine.
    
    Usage:
        # Create USM instance for non-authoritative engine (manager)
        usm = USM(
            username='myuser',
            auth_protocol=AUTH_PROTOCOL_HMACSHA256,
            auth_password='myauthpass',
            priv_protocol=PRIV_PROTOCOL_AESCFB128,
            priv_password='myprivpass'
        )
        
        # Or for authoritative engine (agent)
        usm = USM(
            username='myuser',
            auth_protocol=AUTH_PROTOCOL_HMACSHA256,
            auth_password='myauthpass',
            priv_protocol=PRIV_PROTOCOL_AESCFB128,
            priv_password='myprivpass',
            authoritative=True,
            engine_id=b'\\x80\\x00\\x1f\\x88\\x80...'
        )
    """
    
    # Class variable for engine ID (shared across instances)
    _engine_id_cache = None
    
    def __init__(
        self,
        username: str = '',
        auth_protocol: str = AUTH_PROTOCOL_HMACMD5,
        auth_password: Optional[str] = None,
        auth_key: Optional[bytes] = None,
        priv_protocol: str = PRIV_PROTOCOL_DES,
        priv_password: Optional[str] = None,
        priv_key: Optional[bytes] = None,
        engine_id: Optional[bytes] = None,
        engine_boots: int = 0,
        engine_time: int = 0,
        authoritative: bool = False,
        version: int = SNMP_VERSION_3,
        debug: bool = False
    ):
        """
        Initialize USM Security instance.
        
        Args:
            username: Security name (user name)
            auth_protocol: Authentication protocol OID
            auth_password: Authentication password (will be converted to key)
            auth_key: Pre-computed authentication key (alternative to password)
            priv_protocol: Privacy protocol OID
            priv_password: Privacy password (will be converted to key)
            priv_key: Pre-computed privacy key (alternative to password)
            engine_id: Authoritative snmpEngineID (required for keys)
            engine_boots: Engine boots counter
            engine_time: Engine time in seconds
            authoritative: True if this is an authoritative engine (agent)
            version: SNMP version (should be 3)
            debug: Enable debug output
            
        Raises:
            USMSecurityError: If parameters are invalid or incompatible
        """
        # Basic attributes
        self._error = None
        self._version = version
        self._debug = debug
        self._authoritative = authoritative
        
        # Discovery and synchronization flags
        self._discovered = False       # Engine ID discovered
        self._synchronized = False     # Time synchronized
        
        # Engine parameters
        self._engine_id = engine_id or b''
        self._engine_boots = engine_boots
        self._engine_time = engine_time
        self._latest_engine_time = 0
        self._time_epoch = time.time()
        
        # User credentials
        self._user_name = username
        
        # Authentication configuration
        self._auth_protocol = auth_protocol
        self._auth_password = auth_password
        self._auth_key = auth_key
        self._auth_data = None
        self._auth_maclen = None
        
        # Privacy configuration
        self._priv_protocol = priv_protocol
        self._priv_password = priv_password
        self._priv_key = priv_key
        self._priv_data = None
        
        # Determine security level based on protocols
        self._security_level = self._determine_security_level()
        
        # Validate protocols
        self._validate_auth_protocol()
        self._validate_priv_protocol()
        
        # Generate engine ID if authoritative and not provided
        if self._authoritative and not self._engine_id:
            self._snmp_engine_init()
        
        # Generate keys from passwords if needed
        if self._engine_id:
            if self._auth_password and not self._auth_key:
                self._auth_key_generate()
            if self._priv_password and not self._priv_key:
                self._priv_key_generate()
        
        # Validate keys if provided
        if self._auth_key:
            self._auth_key_validate()
        if self._priv_key:
            self._priv_key_validate()
    
    # ========================================================================
    # Property Accessors
    # ========================================================================
    
    @property
    def error(self) -> Optional[str]:
        """Get the last error message"""
        return self._error
    
    @property
    def version(self) -> int:
        """Get SNMP version"""
        return self._version
    
    @property
    def security_level(self) -> SecurityLevel:
        """Get security level"""
        return self._security_level
    
    @property
    def engine_id(self) -> bytes:
        """Get authoritative engine ID"""
        return self._engine_id
    
    @engine_id.setter
    def engine_id(self, value: bytes):
        """Set authoritative engine ID and regenerate keys"""
        self._engine_id = value
        # Regenerate keys with new engine ID
        if self._auth_password:
            self._auth_key_generate()
        if self._priv_password:
            self._priv_key_generate()
    
    @property
    def engine_boots(self) -> int:
        """Get engine boots counter"""
        return self._engine_boots
    
    @engine_boots.setter
    def engine_boots(self, value: int):
        """Set engine boots counter"""
        self._engine_boots = value
    
    @property
    def engine_time(self) -> int:
        """Get engine time"""
        if self._authoritative:
            # Calculate current time based on epoch
            return int(time.time() - self._time_epoch) + self._engine_time
        return self._engine_time
    
    @engine_time.setter
    def engine_time(self, value: int):
        """Set engine time"""
        self._engine_time = value
        self._time_epoch = time.time()
    
    @property
    def user_name(self) -> str:
        """Get security name (username)"""
        return self._user_name
    
    @property
    def discovered(self) -> bool:
        """Check if engine ID has been discovered"""
        return self._discovered
    
    @property
    def synchronized(self) -> bool:
        """Check if time has been synchronized"""
        return self._synchronized
    
    # ========================================================================
    # Security Level Determination
    # ========================================================================
    
    def _determine_security_level(self) -> SecurityLevel:
        """
        Determine security level based on configured protocols.
        
        Returns:
            SecurityLevel: The appropriate security level
        """
        if self._auth_protocol == AUTH_PROTOCOL_NONE:
            return SECURITY_LEVEL_NOAUTHNOPRIV
        elif self._priv_protocol == PRIV_PROTOCOL_NONE:
            return SECURITY_LEVEL_AUTHNOPRIV
        else:
            return SECURITY_LEVEL_AUTHPRIV
    
    # ========================================================================
    # Protocol Validation
    # ========================================================================
    
    def _validate_auth_protocol(self):
        """Validate authentication protocol"""
        if self._auth_protocol not in AUTH_PROTOCOL_INFO:
            raise USMSecurityError(
                f'Unknown authentication protocol: {self._auth_protocol}'
            )
        
        # Store MAC length for this protocol
        if self._auth_protocol != AUTH_PROTOCOL_NONE:
            self._auth_maclen = AUTH_PROTOCOL_INFO[self._auth_protocol]['mac_length']
    
    def _validate_priv_protocol(self):
        """Validate privacy protocol"""
        if self._priv_protocol not in PRIV_PROTOCOL_INFO:
            raise USMSecurityError(
                f'Unknown privacy protocol: {self._priv_protocol}'
            )
        
        # Check crypto library availability if encryption needed
        if self._priv_protocol != PRIV_PROTOCOL_NONE and not CRYPTO_AVAILABLE:
            raise USMSecurityError(
                'Privacy protocol requires PyCryptodome: pip install pycryptodome'
            )
    
    # ========================================================================
    # Engine Initialization
    # ========================================================================
    
    def _snmp_engine_init(self):
        """
        Initialize SNMP engine ID for authoritative engine.
        
        RFC 3414 Section 5 defines the engine ID format:
        - First 4 octets: Enterprise ID (or format indicator)
        - Remaining octets: Engine-specific identifier
        
        We generate a simple engine ID based on:
        - Format 1 (0x80000000 | enterprise_id)
        - Enterprise ID: 0 (reserved for demo/test)
        - Engine ID: Based on hostname and timestamp
        """
        import socket
        import random
        
        if USM._engine_id_cache:
            self._engine_id = USM._engine_id_cache
            return
        
        # Format 1: IPv4 address
        # First byte: 0x80 (format indicator)
        # Next 3 bytes: Enterprise ID (use 0x000000 for generic)
        # Format: 0x01 (IPv4)
        # Last 4 bytes: IP address
        
        try:
            # Try to get local IP
            hostname = socket.gethostname()
            ip_addr = socket.gethostbyname(hostname)
            ip_bytes = bytes(map(int, ip_addr.split('.')))
            
            # Build engine ID: 0x80 + enterprise(3) + format(1) + ip(4)
            self._engine_id = b'\x80\x00\x00\x00\x01' + ip_bytes
            
        except:
            # Fallback: random engine ID
            # Format 5: Octets administratively assigned
            random_bytes = bytes([random.randint(0, 255) for _ in range(12)])
            self._engine_id = b'\x80\x00\x00\x00\x05' + random_bytes
        
        # Cache for reuse
        USM._engine_id_cache = self._engine_id
        
        # Initialize time tracking
        self._time_epoch = time.time()
        self._engine_boots = 1  # Start at 1 per RFC 3414
    
    # ========================================================================
    # Key Generation (RFC 3414 Section 11.2)
    # ========================================================================
    
    def _auth_key_generate(self):
        """
        Generate authentication key from password.
        
        RFC 3414 Section 11.2 defines the key generation process:
        1. Expand password by repetition to 2^20 octets (1,048,576 bytes)
        2. Hash the expanded password
        3. Localize the hash with engine ID
        
        This process is computationally expensive by design to prevent
        offline dictionary attacks.
        
        Raises:
            USMSecurityError: If engine ID or password not set
        """
        if not self._engine_id or not self._auth_password:
            raise USMSecurityError('Unable to generate authKey: missing engine ID or password')
        
        self._auth_key = self._password_localize(self._auth_password)
        
        if not self._auth_key:
            raise USMSecurityError('Failed to generate authentication key')
    
    def _priv_key_generate(self):
        """
        Generate privacy key from password.
        
        The privacy key is generated similarly to the authentication key,
        but may require extension for longer cipher keys (3DES, AES-192, AES-256).
        
        Key Extension Methods:
        - 3DES/Cisco AES: Chain the password-to-key algorithm
        - Draft AES: Use hash function on localized key
        
        Raises:
            USMSecurityError: If engine ID or password not set
        """
        if not self._engine_id or not self._priv_password:
            raise USMSecurityError('Unable to generate privKey: missing engine ID or password')
        
        # Generate base key
        self._priv_key = self._password_localize(self._priv_password)
        
        if not self._priv_key:
            raise USMSecurityError('Failed to generate privacy key')
        
        # Extend key if needed for longer ciphers
        if self._priv_protocol in [
            PRIV_PROTOCOL_DRAFT_3DESEDE,
            PRIV_PROTOCOL_AESCFB192_CISCO,
            PRIV_PROTOCOL_AESCFB256_CISCO
        ]:
            # Chain algorithm: use output as new input
            self._priv_key += self._password_localize(self._priv_key.decode('latin-1'))
            
        elif self._priv_protocol in [
            PRIV_PROTOCOL_DRAFT_AESCFB192,
            PRIV_PROTOCOL_DRAFT_AESCFB256
        ]:
            # Use hash function on localized key
            info = AUTH_PROTOCOL_INFO[self._auth_protocol]
            hash_func = info['hash_func']
            h = hash_func()
            h.update(self._priv_key)
            self._priv_key += h.digest()
        
        # Truncate to required length
        required_len = PRIV_PROTOCOL_INFO[self._priv_protocol]['key_length']
        self._priv_key = self._priv_key[:required_len]
    
    def _password_localize(self, password: str) -> bytes:
        """
        Localize a password to create a key (RFC 3414 Section 11.2).
        
        Process:
        1. Expand password by repetition to 2^20 octets (1,048,576 bytes)
        2. Compute digest of expanded password
        3. Localize: hash(digest + engine_id + digest)
        
        This creates a key that is:
        - Computationally expensive to brute-force (1M hash operations)
        - Unique to the authoritative engine ID
        - Derived deterministically from the password
        
        Args:
            password: The password to localize
            
        Returns:
            Localized key as bytes
            
        Raises:
            USMSecurityError: If hash function not available
        """
        info = AUTH_PROTOCOL_INFO[self._auth_protocol]
        hash_func = info.get('hash_func')
        
        if not hash_func:
            raise USMSecurityError(
                f'Hash function not available for protocol: {self._auth_protocol}'
            )
        
        # Create hash object
        h = hash_func()
        
        # Expand password to 2^20 octets by repetition
        password_bytes = password.encode('utf-8')
        password_len = len(password_bytes)
        
        # Calculate repetitions needed
        target_size = 2 ** 20  # 1,048,576 bytes
        repetitions = (target_size // password_len) + 1
        expanded = password_bytes * repetitions
        
        # Hash in chunks of 2048 bytes (for memory efficiency)
        chunk_size = 2048
        total_hashed = 0
        
        while total_hashed < target_size:
            chunk = expanded[total_hashed:total_hashed + chunk_size]
            h.update(chunk)
            total_hashed += len(chunk)
        
        # Get initial digest
        digest = h.digest()
        
        # Localize with engine ID
        h = hash_func()
        h.update(digest)
        h.update(self._engine_id)
        h.update(digest)
        
        return h.digest()
    
    # ========================================================================
    # Key Validation
    # ========================================================================
    
    def _auth_key_validate(self):
        """
        Validate authentication key length.
        
        Raises:
            USMSecurityError: If key length is incorrect
        """
        info = AUTH_PROTOCOL_INFO[self._auth_protocol]
        expected_len = info['key_length']
        actual_len = len(self._auth_key)
        
        if actual_len != expected_len:
            raise USMSecurityError(
                f'Invalid {info["name"]} authKey length: {actual_len}, expected {expected_len}'
            )
    
    def _priv_key_validate(self):
        """
        Validate privacy key length and content.
        
        For 3DES, additional validation ensures the three keys are different
        (K1 != K2, K2 != K3, K1 != K3) as required by the draft specification.
        
        Raises:
            USMSecurityError: If key length is incorrect or keys are invalid
        """
        info = PRIV_PROTOCOL_INFO[self._priv_protocol]
        expected_len = info['key_length']
        actual_len = len(self._priv_key)
        
        if actual_len != expected_len:
            raise USMSecurityError(
                f'Invalid {info["name"]} privKey length: {actual_len}, expected {expected_len}'
            )
        
        # Special validation for 3DES
        if self._priv_protocol == PRIV_PROTOCOL_DRAFT_3DESEDE:
            k1 = self._priv_key[0:8]
            k2 = self._priv_key[8:16]
            k3 = self._priv_key[16:24]
            
            if k1 == k2:
                raise USMSecurityError('Invalid CBC-3DES-EDE privKey: K1 equals K2')
            if k2 == k3:
                raise USMSecurityError('Invalid CBC-3DES-EDE privKey: K2 equals K3')
            if k1 == k3:
                raise USMSecurityError('Invalid CBC-3DES-EDE privKey: K1 equals K3')
    
    # ========================================================================
    # Authentication (HMAC) Operations
    # ========================================================================
    
    def generate_auth_key(self, message: bytes) -> bytes:
        """
        Generate authentication MAC for a message (RFC 3414 Section 6).
        
        Process:
        1. Create HMAC using auth key and message
        2. Truncate HMAC to required MAC length (96-384 bits)
        
        The MAC provides:
        - Data integrity: Detects any message modification
        - Data origin authentication: Proves message sender has the key
        
        Args:
            message: The message to authenticate
            
        Returns:
            Truncated HMAC (MAC)
            
        Raises:
            USMSecurityError: If authentication not configured
        """
        if self._auth_protocol == AUTH_PROTOCOL_NONE:
            return b''
        
        if not self._auth_key:
            raise USMSecurityError('Authentication key not available')
        
        info = AUTH_PROTOCOL_INFO[self._auth_protocol]
        hash_func = info['hash_func']
        mac_length = info['mac_length']
        
        # Compute HMAC
        h = hmac.new(self._auth_key, message, hash_func)
        mac = h.digest()
        
        # Truncate to required length
        return mac[:mac_length]
    
    def verify_auth_key(self, message: bytes, received_mac: bytes) -> bool:
        """
        Verify authentication MAC for a received message.
        
        Args:
            message: The received message
            received_mac: The MAC from the message
            
        Returns:
            True if MAC is valid, False otherwise
        """
        if self._auth_protocol == AUTH_PROTOCOL_NONE:
            return True
        
        try:
            expected_mac = self.generate_auth_key(message)
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_mac, received_mac)
        except:
            return False
    
    # ========================================================================
    # Privacy (Encryption/Decryption) Operations
    # ========================================================================
    
    def encrypt(self, plaintext: bytes, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Encrypt data using configured privacy protocol.
        
        Args:
            plaintext: Data to encrypt
            salt: Optional salt/IV (generated if not provided)
            
        Returns:
            Tuple of (ciphertext, salt/IV)
            
        Raises:
            USMSecurityError: If encryption fails
        """
        if self._priv_protocol == PRIV_PROTOCOL_NONE:
            return plaintext, b''
        
        if not self._priv_key:
            raise USMSecurityError('Privacy key not available')
        
        # Generate salt if not provided
        if salt is None:
            salt = self._generate_salt()
        
        if self._priv_protocol == PRIV_PROTOCOL_DES:
            return self._encrypt_des(plaintext, salt), salt
            
        elif self._priv_protocol == PRIV_PROTOCOL_DRAFT_3DESEDE:
            return self._encrypt_3des(plaintext, salt), salt
            
        elif self._priv_protocol in [
            PRIV_PROTOCOL_AESCFB128,
            PRIV_PROTOCOL_DRAFT_AESCFB128,
            PRIV_PROTOCOL_DRAFT_AESCFB192,
            PRIV_PROTOCOL_DRAFT_AESCFB256,
            PRIV_PROTOCOL_AESCFB192_CISCO,
            PRIV_PROTOCOL_AESCFB256_CISCO
        ]:
            return self._encrypt_aes(plaintext, salt), salt
        
        raise USMSecurityError(f'Unsupported privacy protocol: {self._priv_protocol}')
    
    def decrypt(self, ciphertext: bytes, salt: bytes) -> bytes:
        """
        Decrypt data using configured privacy protocol.
        
        Args:
            ciphertext: Data to decrypt
            salt: Salt/IV from the message
            
        Returns:
            Decrypted plaintext
            
        Raises:
            USMSecurityError: If decryption fails
        """
        if self._priv_protocol == PRIV_PROTOCOL_NONE:
            return ciphertext
        
        if not self._priv_key:
            raise USMSecurityError('Privacy key not available')
        
        if self._priv_protocol == PRIV_PROTOCOL_DES:
            return self._decrypt_des(ciphertext, salt)
            
        elif self._priv_protocol == PRIV_PROTOCOL_DRAFT_3DESEDE:
            return self._decrypt_3des(ciphertext, salt)
            
        elif self._priv_protocol in [
            PRIV_PROTOCOL_AESCFB128,
            PRIV_PROTOCOL_DRAFT_AESCFB128,
            PRIV_PROTOCOL_DRAFT_AESCFB192,
            PRIV_PROTOCOL_DRAFT_AESCFB256,
            PRIV_PROTOCOL_AESCFB192_CISCO,
            PRIV_PROTOCOL_AESCFB256_CISCO
        ]:
            return self._decrypt_aes(ciphertext, salt)
        
        raise USMSecurityError(f'Unsupported privacy protocol: {self._priv_protocol}')
    
    def _generate_salt(self) -> bytes:
        """
        Generate salt/IV for encryption.
        
        - DES/3DES: 8 bytes (engine boots + engine time + counter)
        - AES: 8 bytes (engine boots + engine time)
        
        Returns:
            Salt bytes
        """
        import random
        
        # Use engine boots and time if available
        if self._engine_boots and self._engine_time:
            # Pack as network byte order (big-endian)
            boots_time = struct.pack('!II', self._engine_boots, self.engine_time)
            return boots_time
        else:
            # Random salt as fallback
            return bytes([random.randint(0, 255) for _ in range(8)])
    
    # ========================================================================
    # DES Encryption/Decryption (RFC 3414 Section 8.1.1)
    # ========================================================================
    
    def _encrypt_des(self, plaintext: bytes, salt: bytes) -> bytes:
        """Encrypt using DES in CBC mode"""
        if not CRYPTO_AVAILABLE:
            raise USMSecurityError('DES encryption requires PyCryptodome')
        
        # DES key is first 8 bytes of privKey
        des_key = self._priv_key[:8]
        
        # Pre-IV is last 8 bytes of privKey
        pre_iv = self._priv_key[8:16]
        
        # IV = pre_IV XOR salt
        iv = bytes(a ^ b for a, b in zip(pre_iv, salt))
        
        # Pad plaintext to multiple of 8 bytes (DES block size)
        padded = self._pad_pkcs5(plaintext, 8)
        
        # Encrypt
        cipher = DES.new(des_key, DES.MODE_CBC, iv)
        return cipher.encrypt(padded)
    
    def _decrypt_des(self, ciphertext: bytes, salt: bytes) -> bytes:
        """Decrypt using DES in CBC mode"""
        if not CRYPTO_AVAILABLE:
            raise USMSecurityError('DES decryption requires PyCryptodome')
        
        # DES key is first 8 bytes of privKey
        des_key = self._priv_key[:8]
        
        # Pre-IV is last 8 bytes of privKey
        pre_iv = self._priv_key[8:16]
        
        # IV = pre_IV XOR salt
        iv = bytes(a ^ b for a, b in zip(pre_iv, salt))
        
        # Decrypt
        cipher = DES.new(des_key, DES.MODE_CBC, iv)
        padded = cipher.decrypt(ciphertext)
        
        # Remove padding
        return self._unpad_pkcs5(padded)
    
    # ========================================================================
    # 3DES Encryption/Decryption
    # ========================================================================
    
    def _encrypt_3des(self, plaintext: bytes, salt: bytes) -> bytes:
        """Encrypt using 3DES-EDE in CBC mode"""
        if not CRYPTO_AVAILABLE:
            raise USMSecurityError('3DES encryption requires PyCryptodome')
        
        # 3DES key is first 24 bytes of privKey
        des3_key = self._priv_key[:24]
        
        # Pre-IV is last 8 bytes of privKey
        pre_iv = self._priv_key[24:32]
        
        # IV = pre_IV XOR salt
        iv = bytes(a ^ b for a, b in zip(pre_iv, salt))
        
        # Pad plaintext
        padded = self._pad_pkcs5(plaintext, 8)
        
        # Encrypt
        cipher = DES3.new(des3_key, DES3.MODE_CBC, iv)
        return cipher.encrypt(padded)
    
    def _decrypt_3des(self, ciphertext: bytes, salt: bytes) -> bytes:
        """Decrypt using 3DES-EDE in CBC mode"""
        if not CRYPTO_AVAILABLE:
            raise USMSecurityError('3DES decryption requires PyCryptodome')
        
        # 3DES key is first 24 bytes of privKey
        des3_key = self._priv_key[:24]
        
        # Pre-IV is last 8 bytes of privKey
        pre_iv = self._priv_key[24:32]
        
        # IV = pre_IV XOR salt
        iv = bytes(a ^ b for a, b in zip(pre_iv, salt))
        
        # Decrypt
        cipher = DES3.new(des3_key, DES3.MODE_CBC, iv)
        padded = cipher.decrypt(ciphertext)
        
        # Remove padding
        return self._unpad_pkcs5(padded)
    
    # ========================================================================
    # AES Encryption/Decryption (RFC 3826)
    # ========================================================================
    
    def _encrypt_aes(self, plaintext: bytes, salt: bytes) -> bytes:
        """Encrypt using AES in CFB128 mode"""
        if not CRYPTO_AVAILABLE:
            raise USMSecurityError('AES encryption requires PyCryptodome')
        
        # Determine key size
        key_len = PRIV_PROTOCOL_INFO[self._priv_protocol]['key_length']
        aes_key = self._priv_key[:key_len]
        
        # IV = engine boots + engine time + salt (16 bytes total)
        iv = salt + bytes([0] * (16 - len(salt)))
        
        # No padding needed for CFB mode
        cipher = AES.new(aes_key, AES.MODE_CFB, iv, segment_size=128)
        return cipher.encrypt(plaintext)
    
    def _decrypt_aes(self, ciphertext: bytes, salt: bytes) -> bytes:
        """Decrypt using AES in CFB128 mode"""
        if not CRYPTO_AVAILABLE:
            raise USMSecurityError('AES decryption requires PyCryptodome')
        
        # Determine key size
        key_len = PRIV_PROTOCOL_INFO[self._priv_protocol]['key_length']
        aes_key = self._priv_key[:key_len]
        
        # IV = engine boots + engine time + salt (16 bytes total)
        iv = salt + bytes([0] * (16 - len(salt)))
        
        # Decrypt
        cipher = AES.new(aes_key, AES.MODE_CFB, iv, segment_size=128)
        return cipher.decrypt(ciphertext)
    
    # ========================================================================
    # Padding Utilities
    # ========================================================================
    
    def _pad_pkcs5(self, data: bytes, block_size: int) -> bytes:
        """
        Add PKCS#5 padding to data.
        
        PKCS#5 padding adds N bytes of value N, where N is the number
        of bytes needed to reach the next block boundary (1-block_size).
        
        Args:
            data: Data to pad
            block_size: Block size in bytes
            
        Returns:
            Padded data
        """
        padding_len = block_size - (len(data) % block_size)
        padding = bytes([padding_len] * padding_len)
        return data + padding
    
    def _unpad_pkcs5(self, data: bytes) -> bytes:
        """
        Remove PKCS#5 padding from data.
        
        Args:
            data: Padded data
            
        Returns:
            Unpadded data
            
        Raises:
            USMSecurityError: If padding is invalid
        """
        if not data:
            raise USMSecurityError('Cannot unpad empty data')
        
        padding_len = data[-1]
        
        # Validate padding
        if padding_len < 1 or padding_len > len(data):
            raise USMSecurityError('Invalid PKCS#5 padding')
        
        padding = data[-padding_len:]
        if not all(b == padding_len for b in padding):
            raise USMSecurityError('Invalid PKCS#5 padding bytes')
        
        return data[:-padding_len]
    
    # ========================================================================
    # Time Synchronization
    # ========================================================================
    
    def synchronize(self, engine_boots: int, engine_time: int):
        """
        Synchronize engine time parameters.
        
        RFC 3414 Section 3.2.7 requires time synchronization to prevent
        replay attacks. Messages outside the time window (150 seconds)
        are rejected.
        
        Args:
            engine_boots: Authoritative engine boots
            engine_time: Authoritative engine time
        """
        self._engine_boots = engine_boots
        self._engine_time = engine_time
        self._time_epoch = time.time()
        self._latest_engine_time = engine_time
        self._synchronized = True
    
    def is_time_valid(self, boots: int, msg_time: int) -> bool:
        """
        Check if received time parameters are within acceptable window.
        
        RFC 3414 Section 3.2.7:
        - Boots must match
        - Time must be within ±150 seconds
        
        Args:
            boots: Received engine boots
            msg_time: Received engine time
            
        Returns:
            True if time is valid
        """
        if boots != self._engine_boots:
            return False
        
        current_time = self.engine_time
        time_diff = abs(current_time - msg_time)
        
        # RFC 3414: 150 second window
        return time_diff <= 150
    
    # ========================================================================
    # String Representation
    # ========================================================================
    
    def __repr__(self) -> str:
        """String representation of USM instance"""
        return (
            f"USM(user='{self._user_name}', "
            f"level={self._security_level.name}, "
            f"auth={AUTH_PROTOCOL_INFO.get(self._auth_protocol, {}).get('name', 'Unknown')}, "
            f"priv={PRIV_PROTOCOL_INFO.get(self._priv_protocol, {}).get('name', 'Unknown')})"
        )


# ============================================================================
# Module-level Convenience Functions
# ============================================================================

def generate_engine_id() -> bytes:
    """
    Generate a random engine ID.
    
    Returns:
        8-byte engine ID
    """
    import socket
    import random
    
    try:
        # Try to get local IP
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
        ip_bytes = bytes(map(int, ip_addr.split('.')))
        
        # Format: 0x80 + enterprise(3) + format(1) + ip(4)
        return b'\x80\x00\x00\x00\x01' + ip_bytes
        
    except:
        # Fallback: random
        random_bytes = bytes([random.randint(0, 255) for _ in range(12)])
        return b'\x80\x00\x00\x00\x05' + random_bytes


def password_to_key(password: str, engine_id: bytes, auth_protocol: str = AUTH_PROTOCOL_HMACSHA) -> bytes:
    """
    Convert password to localized key.
    
    Args:
        password: Password string
        engine_id: Authoritative engine ID
        auth_protocol: Authentication protocol to use
        
    Returns:
        Localized key bytes
    """
    usm = USM(
        username='temp',
        auth_protocol=auth_protocol,
        auth_password=password,
        engine_id=engine_id
    )
    return usm._auth_key


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    """Example usage demonstrating USM functionality"""
    
    print("SNMPv3 USM Security Module - Example Usage")
    print("=" * 70)
    
    # Example 1: Create USM with password-based authentication
    print("\nExample 1: Password-based Authentication")
    print("-" * 70)
    
    engine_id = generate_engine_id()
    print(f"Generated Engine ID: {engine_id.hex()}")
    
    usm = USM(
        username='admin',
        auth_protocol=AUTH_PROTOCOL_HMACSHA256,
        auth_password='authpassword123',
        priv_protocol=PRIV_PROTOCOL_NONE,  # No encryption for demo
        engine_id=engine_id
    )
    
    print(f"USM Instance: {usm}")
    print(f"Security Level: {usm.security_level.name}")
    print(f"Auth Key (hex): {usm._auth_key.hex()[:32]}...")
    if usm._priv_key:
        print(f"Priv Key (hex): {usm._priv_key.hex()[:32]}...")
    
    # Example 2: Authentication
    print("\nExample 2: Message Authentication")
    print("-" * 70)
    
    message = b"This is a test SNMPv3 message"
    mac = usm.generate_auth_key(message)
    print(f"Message: {message}")
    print(f"Generated MAC: {mac.hex()}")
    
    # Verify MAC
    is_valid = usm.verify_auth_key(message, mac)
    print(f"MAC Verification: {'VALID' if is_valid else 'INVALID'}")
    
    # Example 3: Encryption
    if CRYPTO_AVAILABLE:
        print("\nExample 3: Message Encryption")
        print("-" * 70)
        
        plaintext = b"Confidential SNMP data"
        print(f"Plaintext: {plaintext}")
        
        ciphertext, salt = usm.encrypt(plaintext)
        print(f"Ciphertext (hex): {ciphertext.hex()}")
        print(f"Salt (hex): {salt.hex()}")
        
        decrypted = usm.decrypt(ciphertext, salt)
        print(f"Decrypted: {decrypted}")
        print(f"Match: {plaintext == decrypted}")
    else:
        print("\nExample 3: Encryption (PyCryptodome not available)")
        print("Install with: pip install pycryptodome")
    
    # Example 4: Different protocols
    print("\nExample 4: Protocol Support")
    print("-" * 70)
    
    protocols = [
        ("HMAC-MD5", AUTH_PROTOCOL_HMACMD5),
        ("HMAC-SHA-1", AUTH_PROTOCOL_HMACSHA),
        ("HMAC-SHA-256", AUTH_PROTOCOL_HMACSHA256),
        ("HMAC-SHA-512", AUTH_PROTOCOL_HMACSHA512),
    ]
    
    for name, protocol in protocols:
        info = AUTH_PROTOCOL_INFO[protocol]
        print(f"{name:20} Key: {info['key_length']:2d} bytes, MAC: {info['mac_length']:2d} bytes")
    
    print("\n" + "=" * 70)
    print("USM module ready for production use!")