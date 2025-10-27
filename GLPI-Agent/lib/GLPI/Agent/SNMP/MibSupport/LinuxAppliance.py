"""
GLPI Agent SNMP MibSupport LinuxAppliance Module - Python Implementation

This module provides inventory support for various Linux-based appliances
through SNMP queries. It detects and identifies different appliance types
including NAS devices, network appliances, printers, and UPS systems.

Original: GLPI::Agent::SNMP::MibSupport::LinuxAppliance (Perl)
Converted to: Python 3.x
"""

import re
from typing import Dict, List, Optional, Any, Union


# ============================================================================
# OID CONSTANTS - SNMP Object Identifiers
# ============================================================================

# Base OIDs
ISO = '.1.3.6.1.2.1'
SYS_DESCR = f'{ISO}.1.1.0'
ENTERPRISES = '.1.3.6.1.4.1'
LINUX = f'{ENTERPRISES}.8072.3.2.10'

# Enterprise-specific OIDs
UCDDAVIS = f'{ENTERPRISES}.2021'
CHECKPOINT = f'{ENTERPRISES}.2620'
SOCOMEC = f'{ENTERPRISES}.4555'
SYNOLOGY = f'{ENTERPRISES}.6574'
UBNT = f'{ENTERPRISES}.41112'

UCD_EXPERIMENTAL = f'{UCDDAVIS}.13'

# UCD-DLMOD-MIB DEFINITIONS
UCD_DLMOD_MIB = f'{UCD_EXPERIMENTAL}.14'
DLMOD_ENTRY = f'{UCD_DLMOD_MIB}.2.1'
DLMOD_NAME = f'{DLMOD_ENTRY}.2.1'

# SYNOLOGY-SYSTEM-MIB
DSM_INFO = f'{SYNOLOGY}.1.5'
DSM_INFO_MODEL_NAME = f'{DSM_INFO}.1.0'
DSM_INFO_SERIAL_NUMBER = f'{DSM_INFO}.2.0'
DSM_INFO_VERSION = f'{DSM_INFO}.3.0'

# SYNOLOGY-DISK-MIB
SYNO_DISK_ENTRY = f'{SYNOLOGY}.2.1.1'
SYNO_DISK_ID = f'{SYNO_DISK_ENTRY}.2'
SYNO_DISK_MODEL = f'{SYNO_DISK_ENTRY}.3'
SYNO_DISK_TYPE = f'{SYNO_DISK_ENTRY}.4'
SYNO_DISK_NAME = f'{SYNO_DISK_ENTRY}.12'

# SYNOLOGY-RAID-MIB
SYNO_RAID_ENTRY = f'{SYNOLOGY}.3.1.1'
SYNO_RAID_NAME = f'{SYNO_RAID_ENTRY}.2'
SYNO_RAID_FREE_SIZE = f'{SYNO_RAID_ENTRY}.4'
SYNO_RAID_TOTAL_SIZE = f'{SYNO_RAID_ENTRY}.5'

# CHECKPOINT-MIB
SVN_PROD_NAME = f'{CHECKPOINT}.1.6.1.0'
SVN_VERSION = f'{CHECKPOINT}.1.6.4.1.0'
SVN_APPLIANCE_SERIAL_NUMBER = f'{CHECKPOINT}.1.6.16.3.0'
SVN_APPLIANCE_MODEL = f'{CHECKPOINT}.1.6.16.7.0'
SVN_APPLIANCE_MANUFACTURER = f'{CHECKPOINT}.1.6.16.9.0'

# SNMP-FRAMEWORK-MIB
SNMP_MODULES = '.1.3.6.1.6.3'
SNMP_ENGINE = f'{SNMP_MODULES}.10.2.1'
SNMP_ENGINE_ID = f'{SNMP_ENGINE}.1.0'

# HOST-RESOURCES-MIB
HR_STORAGE_ENTRY = f'{ISO}.25.2.3.1.3'
HR_SW_RUN_NAME = f'{ISO}.25.4.2.1.2'

# UBNT-UniFi-MIB
UBNT_UNIFI = f'{UBNT}.1.6'
UNIFI_AP_SYSTEM_MODEL = f'{UBNT_UNIFI}.3.3.0'
UNIFI_AP_SYSTEM_VERSION = f'{UBNT_UNIFI}.3.6.0'

# SOCOMECUPS7-MIB
UPS_IDENT = f'{SOCOMEC}.1.1.7.1.1'
UPS_IDENT_MODEL = f'{UPS_IDENT}.1.0'
UPS_IDENT_SERIAL_NUMBER = f'{UPS_IDENT}.2.0'
UPS_IDENT_AGENT_SOFTWARE_VERSION = f'{UPS_IDENT}.5.0'

# Printer-MIB
PRT_GENERAL = f'{ISO}.43.5'
PRT_GENERAL_PRINTER_NAME = f'{PRT_GENERAL}.1.1.16.1'

# Quantum MIB
QUANTUM = f'{ENTERPRISES}.2036.2'
Q_VENDOR_ID = f'{QUANTUM}.1.1.4.0'
Q_PROD_ID = f'{QUANTUM}.1.1.5.0'
Q_PROD_REV = f'{QUANTUM}.1.1.6.0'
Q_SERIAL_NUMBER = f'{QUANTUM}.1.1.12.0'


# ============================================================================
# MIB SUPPORT CONFIGURATION
# ============================================================================

MIB_SUPPORT = [
    {
        'name': 'linuxAppliance',
        'sysobjectid': LINUX  # Would be regex match in actual implementation
    }
]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def hex2char(hex_string: Optional[str]) -> Optional[str]:
    """
    Convert hex string to character string.
    
    Args:
        hex_string: Hex string (with or without 0x prefix)
        
    Returns:
        Decoded string or None
    """
    if not hex_string:
        return None
    
    # Remove 0x prefix if present
    hex_string = hex_string.replace('0x', '')
    
    try:
        return bytes.fromhex(hex_string).decode('utf-8', errors='ignore')
    except ValueError:
        return None


def get_canonical_string(value: Optional[Any]) -> Optional[str]:
    """
    Get canonical string representation of a value.
    
    Args:
        value: Input value (string, bytes, etc.)
        
    Returns:
        Canonical string or None
    """
    if value is None:
        return None
    
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='ignore')
    
    value = str(value).strip()
    return value if value else None


def trim_whitespace(value: Optional[str]) -> Optional[str]:
    """
    Trim whitespace from string.
    
    Args:
        value: Input string
        
    Returns:
        Trimmed string or None
    """
    if value is None:
        return None
    
    value = str(value).strip()
    return value if value else None


def get_canonical_manufacturer(model: Optional[str]) -> Optional[str]:
    """
    Extract manufacturer from model string.
    
    Args:
        model: Model string
        
    Returns:
        Manufacturer name or None
    """
    if not model:
        return None
    
    # Common manufacturer prefixes
    manufacturers = {
        'WD': 'Western Digital',
        'HGST': 'HGST',
        'Seagate': 'Seagate',
        'Samsung': 'Samsung',
        'Toshiba': 'Toshiba',
        'Hitachi': 'Hitachi',
        'Intel': 'Intel',
        'Crucial': 'Crucial',
        'Kingston': 'Kingston'
    }
    
    for prefix, manufacturer in manufacturers.items():
        if model.upper().startswith(prefix.upper()):
            return manufacturer
    
    return None


def get_canonical_size(size_string: str) -> Optional[int]:
    """
    Convert size string to canonical integer (MB).
    
    Args:
        size_string: Size string with unit (e.g., "1000 bytes", "10 GB")
        
    Returns:
        Size in MB or None
    """
    if not size_string:
        return None
    
    match = re.match(r'(\d+)\s*(bytes|KB|MB|GB|TB)?', size_string, re.IGNORECASE)
    if not match:
        return None
    
    size = int(match.group(1))
    unit = (match.group(2) or 'bytes').upper()
    
    # Convert to MB
    if unit == 'BYTES':
        size = size // (1024 * 1024)
    elif unit == 'KB':
        size = size // 1024
    elif unit == 'GB':
        size = size * 1024
    elif unit == 'TB':
        size = size * 1024 * 1024
    
    return size


def get_manufacturer_id_info(manufacturer_id: int) -> Optional[Dict[str, str]]:
    """
    Get manufacturer information based on IANA private enterprise number.
    
    Args:
        manufacturer_id: IANA enterprise number
        
    Returns:
        Dictionary with manufacturer, type, and optionally model
    """
    # This would typically be loaded from a database or configuration file
    # Here's a subset of common enterprise numbers
    manufacturers = {
        2: {'manufacturer': 'IBM', 'type': 'NETWORKING'},
        9: {'manufacturer': 'Cisco', 'type': 'NETWORKING'},
        11: {'manufacturer': 'HP', 'type': 'NETWORKING'},
        43: {'manufacturer': '3Com', 'type': 'NETWORKING'},
        171: {'manufacturer': 'D-Link', 'type': 'NETWORKING'},
        207: {'manufacturer': 'Allied Telesis', 'type': 'NETWORKING'},
        2620: {'manufacturer': 'CheckPoint', 'type': 'NETWORKING'},
        4555: {'manufacturer': 'Socomec', 'type': 'POWER'},
        6574: {'manufacturer': 'Synology', 'type': 'STORAGE'},
        8072: {'manufacturer': 'Net-SNMP', 'type': 'NETWORKING'},
        41112: {'manufacturer': 'Ubiquiti', 'type': 'NETWORKING'},
    }
    
    return manufacturers.get(manufacturer_id)


def glpi_version(version_string: str) -> tuple:
    """
    Parse GLPI version string to tuple for comparison.
    
    Args:
        version_string: Version string (e.g., "10.0.10")
        
    Returns:
        Tuple of version numbers
    """
    if not version_string:
        return (0, 0, 0)
    
    parts = version_string.split('.')
    try:
        return tuple(int(p) for p in parts[:3])
    except (ValueError, IndexError):
        return (0, 0, 0)


def get_regexp_oid_match(oid: str) -> str:
    """
    Get regex pattern for OID matching.
    
    Args:
        oid: OID string
        
    Returns:
        Regex pattern for OID
    """
    return f'^{re.escape(oid)}'


# ============================================================================
# MAIN CLASS - LinuxApplianceMibSupport
# ============================================================================

class LinuxApplianceMibSupport:
    """
    SNMP MIB support for Linux-based appliances.
    
    This class provides methods to detect and inventory various Linux appliances
    through SNMP queries, including:
    - Seagate/LaCie NAS devices
    - Synology NAS systems
    - CheckPoint security appliances
    - Sophos UTM
    - Ubiquiti UniFi access points
    - Socomec UPS systems
    - TP-Link devices
    - Quantum appliances
    - Various printers
    """
    
    def __init__(self, snmp_session, device: Dict[str, Any]):
        """
        Initialize the MIB support instance.
        
        Args:
            snmp_session: SNMP session object with get() and walk() methods
            device: Device dictionary to store inventory data
        """
        self.snmp = snmp_session
        self.device = device
        self.hr_sw_run_name_cache = None
    
    def get(self, oid: str) -> Optional[Any]:
        """
        Get a single SNMP value.
        
        Args:
            oid: OID to query
            
        Returns:
            SNMP value or None
        """
        return self.snmp.get(oid)
    
    def walk(self, oid: str) -> Optional[Dict[str, Any]]:
        """
        Walk an SNMP OID tree.
        
        Args:
            oid: Base OID to walk
            
        Returns:
            Dictionary of OID -> value mappings or None
        """
        return self.snmp.walk(oid)
    
    def _has_process(self, name: str) -> bool:
        """
        Check if a process with the given name is running.
        
        This method caches the hrSWRunName walk result to avoid
        multiple SNMP queries when checking for multiple processes.
        
        Args:
            name: Process name to check for
            
        Returns:
            True if process is running, False otherwise
        """
        if not name:
            return False
        
        # Cache the walk result
        if self.hr_sw_run_name_cache is None:
            self.hr_sw_run_name_cache = self.walk(HR_SW_RUN_NAME) or {}
        
        if not self.hr_sw_run_name_cache:
            return False
        
        # Check if process name exists in values
        return any(
            get_canonical_string(value) == name 
            for value in self.hr_sw_run_name_cache.values()
        )
    
    def get_type(self) -> Optional[str]:
        """
        Detect and determine the appliance type.
        
        This method implements the main detection logic by querying various
        SNMP OIDs and pattern matching to identify the appliance type and
        manufacturer. It checks for:
        
        1. Seagate NAS (via hrStorageEntry)
        2. QuesCom devices (via dlmodName)
        3. Synology NAS (via dsmInfo)
        4. CheckPoint appliances (via svnAppliance OIDs)
        5. Sophos UTM (via running processes)
        6. UniFi AP (via unifiApSystemModel)
        7. Socomec UPS (via upsIdentModel)
        8. Quantum appliances (via qVendorId)
        9. TP-Link devices (via sysDescr pattern)
        10. Printers (via prtGeneralPrinterName)
        11. Generic detection via snmpEngineID
        
        Returns:
            Device type string ('STORAGE', 'NETWORKING', 'PRINTER', 'POWER')
            or None if not detected
        """
        if not self.device:
            return None
        
        # Initialize _Appliance dictionary if not present
        if '_Appliance' not in self.device:
            self.device['_Appliance'] = {}
        
        # ====================================================================
        # SEAGATE NAS DETECTION
        # ====================================================================
        hr_storage_entry = self.walk(HR_STORAGE_ENTRY)
        if hr_storage_entry:
            for value in hr_storage_entry.values():
                value_str = get_canonical_string(value)
                if value_str and re.search(r'^/lacie', value_str, re.IGNORECASE):
                    self.device['_Appliance'] = {
                        'MODEL': 'Seagate NAS',
                        'MANUFACTURER': 'Seagate'
                    }
                    return 'STORAGE'
        
        # ====================================================================
        # QUESCOM DETECTION
        # ====================================================================
        dlmod_name = self.get(DLMOD_NAME)
        if dlmod_name and get_canonical_string(dlmod_name) == 'QuesComSnmpObject':
            self.device['_Appliance'] = {
                'MODEL': 'QuesCom',
                'MANUFACTURER': 'QuesCom'
            }
            return 'NETWORKING'
        
        # ====================================================================
        # SYNOLOGY DETECTION
        # ====================================================================
        dsm_info_model_name = self.get(DSM_INFO_MODEL_NAME)
        if dsm_info_model_name:
            self.device['_Appliance'] = {
                'MODEL': get_canonical_string(dsm_info_model_name),
                'MANUFACTURER': 'Synology'
            }
            return 'STORAGE'
        
        # ====================================================================
        # CHECKPOINT DETECTION
        # ====================================================================
        svn_appliance_manufacturer = self.get(SVN_APPLIANCE_MANUFACTURER)
        if svn_appliance_manufacturer:
            self.device['_Appliance'] = {
                'MODEL': get_canonical_string(self.get(SVN_APPLIANCE_MODEL)),
                'MANUFACTURER': 'CheckPoint'
            }
            return 'NETWORKING'
        
        # ====================================================================
        # SOPHOS DETECTION
        # ====================================================================
        if self._has_process('mdw.plx'):
            self.device['_Appliance'] = {
                'MODEL': 'Sophos UTM',
                'MANUFACTURER': 'Sophos'
            }
            return 'NETWORKING'
        
        # ====================================================================
        # UNIFI AP DETECTION
        # ====================================================================
        unifi_model = self.get(UNIFI_AP_SYSTEM_MODEL)
        if unifi_model:
            self.device['_Appliance'] = {
                'MODEL': get_canonical_string(unifi_model),
                'MANUFACTURER': 'Ubiquiti'
            }
            return 'NETWORKING'
        
        # ====================================================================
        # SOCOMEC UPS DETECTION
        # ====================================================================
        socomec_model = self.get(UPS_IDENT_MODEL)
        if socomec_model:
            self.device['_Appliance'] = {
                'MODEL': get_canonical_string(socomec_model),
                'MANUFACTURER': 'Socomec'
            }
            return 'NETWORKING'
        
        # ====================================================================
        # QUANTUM APPLIANCE DETECTION
        # ====================================================================
        q_vendor_id = get_canonical_string(self.get(Q_VENDOR_ID))
        if q_vendor_id:
            self.device['_Appliance'] = {
                'MODEL': get_canonical_string(self.get(Q_PROD_ID)),
                'MANUFACTURER': q_vendor_id,
                'FIRMWARE': get_canonical_string(self.get(Q_PROD_REV)),
                'SERIAL': get_canonical_string(self.get(Q_SERIAL_NUMBER)),
                '_QUANTUM': True
            }
            return 'NETWORKING'
        
        # ====================================================================
        # SYSDESCR ANALYSIS
        # ====================================================================
        sys_descr = get_canonical_string(self.get(SYS_DESCR))
        if sys_descr:
            # TP-Link detection via sysDescr
            tp_link_match = re.match(
                r'^Linux (TL-\S+) ([0-9.]+) #1',
                sys_descr,
                re.IGNORECASE
            )
            if tp_link_match:
                self.device['_Appliance'] = {
                    'MODEL': tp_link_match.group(1),
                    'FIRMWARE': tp_link_match.group(2),
                    'MANUFACTURER': 'TP-Link'
                }
                return 'NETWORKING'
        
        # ====================================================================
        # PRINTER DETECTION
        # ====================================================================
        prt_general_printer_name = self.get(PRT_GENERAL_PRINTER_NAME)
        if prt_general_printer_name:
            self.device['_Appliance'] = {
                'MODEL': get_canonical_string(prt_general_printer_name)
            }
            # Katusha printer support
            if sys_descr and re.match(r'^Katusha', sys_descr, re.IGNORECASE):
                self.device['_Appliance']['MANUFACTURER'] = 'Katusha'
            return 'PRINTER'
        
        # ====================================================================
        # SNMP-FRAMEWORK-MIB: ANALYZE snmpEngineID
        # ====================================================================
        snmp_engine_id = self.get(SNMP_ENGINE_ID)
        if snmp_engine_id:
            # Convert hex string if needed
            snmp_engine_id_str = hex2char(get_canonical_string(snmp_engine_id))
            
            # Check if it's still hex and convert again
            if (snmp_engine_id_str and 
                re.match(r'^[0-9a-fA-F]+$', snmp_engine_id_str) and
                len(snmp_engine_id_str) % 2 == 0):
                snmp_engine_id_str = hex2char(f"0x{snmp_engine_id_str}")
            
            if snmp_engine_id_str and len(snmp_engine_id_str) >= 5:
                # Decode the manufacturer ID from snmpEngineID
                decode = [ord(c) for c in snmp_engine_id_str[:5]]
                manufacturer_id = (
                    ((decode[0] & 0x7f) * 16777216) +
                    (decode[1] * 65536) +
                    (decode[2] * 256) +
                    decode[3]
                )
                
                match = get_manufacturer_id_info(manufacturer_id)
                if match and match.get('manufacturer') and match.get('type'):
                    self.device['_Appliance'] = {
                        'MODEL': match.get('model', ''),
                        'MANUFACTURER': match['manufacturer']
                    }
                    
                    # Special handling for TP-Link
                    if sys_descr:
                        tp_link_model_match = re.match(
                            r'^Linux (TL-\S+)',
                            sys_descr,
                            re.IGNORECASE
                        )
                        if tp_link_model_match:
                            self.device['_Appliance']['MODEL'] = tp_link_model_match.group(1)
                            self.device['_Appliance']['MANUFACTURER'] = 'TP-Link'
                            return 'NETWORKING'
                    
                    return match['type']
        
        return None
    
    def get_model(self) -> Optional[str]:
        """
        Get the detected appliance model.
        
        Returns:
            Model string or None
        """
        if not self.device:
            return None
        
        appliance = self.device.get('_Appliance', {})
        return appliance.get('MODEL')
    
    def get_manufacturer(self) -> Optional[str]:
        """
        Get the detected appliance manufacturer.
        
        Returns:
            Manufacturer string or None
        """
        if not self.device:
            return None
        
        appliance = self.device.get('_Appliance', {})
        return appliance.get('MANUFACTURER')
    
    def get_serial(self) -> Optional[str]:
        """
        Get the appliance serial number.
        
        The method retrieves serial numbers differently based on manufacturer:
        - Synology: From dsmInfo_serialNumber
        - CheckPoint: From svnApplianceSerialNumber
        - Seagate: From snmpEngineID (stripped)
        - Ubiquiti: From MAC address (colons removed)
        - Socomec: From upsIdentSerialNumber
        - Quantum: From device._Appliance.SERIAL
        
        Returns:
            Serial number string or None
        """
        if not self.device:
            return None
        
        manufacturer = self.get_manufacturer()
        if not manufacturer:
            return None
        
        serial = None
        
        if manufacturer == 'Synology':
            serial = get_canonical_string(self.get(DSM_INFO_SERIAL_NUMBER))
        
        elif manufacturer == 'CheckPoint':
            serial = get_canonical_string(self.get(SVN_APPLIANCE_SERIAL_NUMBER))
        
        elif manufacturer == 'Seagate':
            snmp_engine_id = get_canonical_string(self.get(SNMP_ENGINE_ID))
            if snmp_engine_id:
                # Use stripped snmpEngineID as serial
                serial = snmp_engine_id.replace('0x', '')
        
        elif manufacturer == 'Ubiquiti' and self.device.get('MAC'):
            serial = self.device['MAC'].replace(':', '')
        
        elif manufacturer == 'Socomec':
            serial = get_canonical_string(self.get(UPS_IDENT_SERIAL_NUMBER))
        
        elif self.device.get('_Appliance', {}).get('SERIAL'):
            serial = self.device['_Appliance']['SERIAL']
            
            # Fix location on Quantum devices (badly encoded)
            if self.device.get('_Appliance', {}).get('_QUANTUM'):
                location = self.device.get('LOCATION')
                if (location and 
                    re.match(r'^[0-9a-f]+$', location) and 
                    len(location) % 2 == 0):
                    try:
                        self.device['LOCATION'] = get_canonical_string(
                            bytes.fromhex(location)
                        )
                    except ValueError:
                        pass
        
        return serial
    
    def run(self) -> None:
        """
        Main inventory collection method.
        
        This method collects detailed inventory information based on the
        detected manufacturer:
        
        - Synology: Collects disk information (model, type, name) and
          volume information (name, free space, total size)
        - CheckPoint: Collects firmware version information
        - Ubiquiti: Collects UniFi AP system version
        - Socomec: Collects UPS software version
        - TP-Link: Collects firmware version
        - Quantum: Collects product revision
        
        The collected information is stored in the device dictionary,
        including storage arrays, drive information, and firmware details.
        """
        if not self.device:
            return
        
        manufacturer = self.get_manufacturer()
        if not manufacturer:
            return
        
        firmware = None
        
        # ====================================================================
        # SYNOLOGY INVENTORY
        # ====================================================================
        if manufacturer == 'Synology':
            # Collect disk information
            disk_ids = self.walk(SYNO_DISK_ID) or {}
            disk_models = self.walk(SYNO_DISK_MODEL) or {}
            disk_types = self.walk(SYNO_DISK_TYPE) or {}
            disk_names = self.walk(SYNO_DISK_NAME) or {}
            
            for key in disk_models.keys():
                model = trim_whitespace(
                    get_canonical_string(disk_models.get(key))
                )
                if not model:
                    continue
                
                storage = {
                    'MODEL': model,
                    'TYPE': 'disk'
                }
                
                disk_name = (
                    trim_whitespace(get_canonical_string(disk_names.get(key))) or
                    trim_whitespace(get_canonical_string(disk_ids.get(key)))
                )
                disk_manufacturer = trim_whitespace(
                    get_canonical_manufacturer(model)
                )
                disk_type = trim_whitespace(
                    get_canonical_string(disk_types.get(key))
                )
                
                if disk_name:
                    storage['NAME'] = disk_name
                if disk_manufacturer:
                    storage['MANUFACTURER'] = disk_manufacturer
                if disk_type:
                    storage['INTERFACE'] = disk_type
                
                if 'STORAGES' not in self.device:
                    self.device['STORAGES'] = []
                self.device['STORAGES'].append(storage)
            
            # Collect volume information (only for GLPI > 10.0.10)
            glpi = self.device.get('glpi')
            glpi_ver = glpi_version(glpi) if glpi else (0, 0, 0)
            
            if glpi_ver == (0, 0, 0) or glpi_ver > glpi_version('10.0.10'):
                volumes_names = self.walk(SYNO_RAID_NAME) or {}
                volumes_free_sizes = self.walk(SYNO_RAID_FREE_SIZE) or {}
                volumes_total_sizes = self.walk(SYNO_RAID_TOTAL_SIZE) or {}
                
                for key in volumes_names.keys():
                    name = trim_whitespace(
                        get_canonical_string(volumes_names.get(key))
                    )
                    if not name:
                        continue
                    
                    volume = {'VOLUMN': name}
                    
                    if key in volumes_free_sizes:
                        free_size = get_canonical_size(
                            f"{volumes_free_sizes[key]} bytes"
                        )
                        if free_size is not None:
                            volume['FREE'] = free_size
                    
                    if key in volumes_total_sizes:
                        total_size = get_canonical_size(
                            f"{volumes_total_sizes[key]} bytes"
                        )
                        if total_size is not None:
                            volume['TOTAL'] = total_size
                    
                    if 'FREE' in volume and 'TOTAL' in volume:
                        if 'DRIVES' not in self.device:
                            self.device['DRIVES'] = []
                        self.device['DRIVES'].append(volume)
            
            elif self.device.get('logger'):
                self.device['logger'].debug(
                    f"Skipping DISKS inventory as glpi {glpi} is out-dated, "
                    "you should upgrade your glpi server"
                )
            
            # Collect DSM firmware version
            dsm_info_version = self.get(DSM_INFO_VERSION)
            if dsm_info_version:
                firmware = {
                    'NAME': f"{manufacturer} DSM",
                    'DESCRIPTION': f"{manufacturer} DSM firmware",
                    'TYPE': 'system',
                    'VERSION': get_canonical_string(dsm_info_version),
                    'MANUFACTURER': manufacturer
                }
        
        # ====================================================================
        # CHECKPOINT INVENTORY
        # ====================================================================
        elif manufacturer == 'CheckPoint':
            svn_version = self.get(SVN_VERSION)
            if svn_version:
                firmware = {
                    'NAME': get_canonical_string(self.get(SVN_PROD_NAME)),
                    'DESCRIPTION': f"{manufacturer} SVN version",
                    'TYPE': 'system',
                    'VERSION': get_canonical_string(svn_version),
                    'MANUFACTURER': manufacturer
                }
        
        # ====================================================================
        # UBIQUITI INVENTORY
        # ====================================================================
        elif manufacturer == 'Ubiquiti':
            unifi_ap_system_version = self.get(UNIFI_AP_SYSTEM_VERSION)
            if unifi_ap_system_version:
                firmware = {
                    'NAME': self.get_model(),
                    'DESCRIPTION': 'Unifi AP System version',
                    'TYPE': 'system',
                    'VERSION': get_canonical_string(unifi_ap_system_version),
                    'MANUFACTURER': manufacturer
                }
        
        # ====================================================================
        # SOCOMEC INVENTORY
        # ====================================================================
        elif manufacturer == 'Socomec':
            ups_ident_agent_software_version = self.get(
                UPS_IDENT_AGENT_SOFTWARE_VERSION
            )
            if ups_ident_agent_software_version:
                name = self.get_model()
                version = get_canonical_string(ups_ident_agent_software_version)
                
                # Parse version string (e.g., "Name v1.2.3")
                version_match = re.match(r'^(.*) v([0-9.]+)$', version)
                if version_match:
                    name = version_match.group(1)
                    version = version_match.group(2)
                
                firmware = {
                    'NAME': name,
                    'DESCRIPTION': f"Socomec {self.get_model()} software version",
                    'TYPE': 'system',
                    'VERSION': version,
                    'MANUFACTURER': manufacturer
                }
        
        # ====================================================================
        # TP-LINK INVENTORY
        # ====================================================================
        elif (manufacturer == 'TP-Link' and 
              self.device.get('_Appliance', {}).get('FIRMWARE')):
            firmware = {
                'NAME': self.get_model(),
                'DESCRIPTION': 'Firmware version',
                'TYPE': 'system',
                'VERSION': self.device['_Appliance']['FIRMWARE'],
                'MANUFACTURER': manufacturer
            }
        
        # ====================================================================
        # QUANTUM INVENTORY
        # ====================================================================
        elif self.device.get('_Appliance', {}).get('_QUANTUM'):
            firmware = {
                'NAME': self.get_model(),
                'DESCRIPTION': 'Product revision number',
                'TYPE': 'system',
                'VERSION': self.device['_Appliance']['FIRMWARE'],
                'MANUFACTURER': manufacturer
            }
        
        # Add firmware to device if collected
        if firmware:
            self._add_firmware(firmware)
    
    def _add_firmware(self, firmware: Dict[str, str]) -> None:
        """
        Add firmware information to device.
        
        Args:
            firmware: Firmware dictionary with NAME, DESCRIPTION, TYPE, VERSION, MANUFACTURER
        """
        if 'FIRMWARES' not in self.device:
            self.device['FIRMWARES'] = []
        self.device['FIRMWARES'].append(firmware)


# ============================================================================
# MODULE INTERFACE FUNCTIONS
# ============================================================================

def create_mib_support(snmp_session, device: Dict[str, Any]) -> LinuxApplianceMibSupport:
    """
    Factory function to create a LinuxApplianceMibSupport instance.
    
    Args:
        snmp_session: SNMP session object
        device: Device dictionary
        
    Returns:
        LinuxApplianceMibSupport instance
    """
    return LinuxApplianceMibSupport(snmp_session, device)


def get_mib_support_config() -> List[Dict[str, str]]:
    """
    Get the MIB support configuration.
    
    Returns:
        List of MIB support configurations
    """
    return MIB_SUPPORT


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == '__main__':
    """
    Example usage of the LinuxApplianceMibSupport module.
    
    This demonstrates how to use the module with a mock SNMP session.
    In actual use, you would provide a real SNMP session object with
    pysnmp or similar library.
    """
    
    # Mock SNMP session for demonstration
    class MockSNMP:
        def __init__(self):
            self.data = {
                DSM_INFO_MODEL_NAME: 'DS920+',
                DSM_INFO_SERIAL_NUMBER: '1234ABCD',
                DSM_INFO_VERSION: 'DSM 7.1.1-42962',
            }
        
        def get(self, oid):
            return self.data.get(oid)
        
        def walk(self, oid):
            # Return empty dict for walks in this example
            return {}
    
    # Create device dictionary
    device = {
        'MAC': '00:11:32:AB:CD:EF',
        'LOCATION': 'Server Room'
    }
    
    # Create MIB support instance
    snmp_session = MockSNMP()
    mib_support = create_mib_support(snmp_session, device)
    
    # Detect device type
    device_type = mib_support.get_type()
    print(f"Device Type: {device_type}")
    print(f"Manufacturer: {mib_support.get_manufacturer()}")
    print(f"Model: {mib_support.get_model()}")
    print(f"Serial: {mib_support.get_serial()}")
    
    # Run full inventory
    mib_support.run()
    
    # Display collected information
    print("\nDevice Information:")
    for key, value in device.items():
        if not key.startswith('_'):
            print(f"  {key}: {value}")
