import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import re

# Mock implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

def empty(value):
    return value is None or str(value).strip() == ''

def get_regexp_oid_match(oid):
    # Assuming it returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns a mock value to test functionality
        mock_values = {
            ".1.3.6.1.4.1.6889.2.69.6.1.4.0": "1.2.3",
            ".1.3.6.1.4.1.6889.2.69.6.1.27.0": "DSP 4.5",
            ".1.3.6.1.4.1.6889.2.69.6.1.52.0": "J100",
            ".1.3.6.1.4.1.6889.2.69.6.1.57.0": "SN123456",
            ".1.3.6.1.4.1.6889.2.69.6.1.139.0": "HW 1.0",
            ".1.3.6.1.4.1.6889.2.69.6.1.168.0": "OpenSSL 1.1.1",
            ".1.3.6.1.4.1.6889.2.69.6.1.169.0": "OpenSSH 8.0"
        }
        return mock_values.get(oid, None)

# Configure module logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ============================================================================
# Constants from Avaya-J100IpPhone-MIB
# ============================================================================

AVAYA = ".1.3.6.1.4.1.6889"

# Product identifiers
PRODUCTS = AVAYA + ".1"
AVAYA_IP_ENDPOINT_PROD = PRODUCTS + ".69"
AVAYA_96X1_SIP_ENDPOINTS = AVAYA_IP_ENDPOINT_PROD + ".6"

# MIB identifiers
AVAYA_MIBS = AVAYA + ".2"
IP_ENDPOINT_MIBS = AVAYA_MIBS + ".69"
AVAYA_SPARK_MIB = IP_ENDPOINT_MIBS + ".6"

# Endpoint identification OIDs
ENDPT_ID = AVAYA_SPARK_MIB + ".1"
ENDPT_APPINUSE = ENDPT_ID + ".4.0"           # Application/Firmware in use
ENDPT_DSPVERSION = ENDPT_ID + ".27.0"        # DSP firmware version
ENDPT_MODEL = ENDPT_ID + ".52.0"             # Phone model
ENDPT_PHONESN = ENDPT_ID + ".57.0"           # Phone serial number
ENDPT_HWVER = ENDPT_ID + ".139.0"            # Hardware version
ENDPT_OPENSSL_VERSION = ENDPT_ID + ".168.0"  # OpenSSL version
ENDPT_OPENSSH_VERSION = ENDPT_ID + ".169.0"  # OpenSSH version

# MIB support configuration
mib_support = [
    {
        "name": "avaya-j100-ipphone",
        "sysobjectid": get_regexp_oid_match(AVAYA_96X1_SIP_ENDPOINTS),
        "manufacturer": "Avaya"
    }
]


# ============================================================================
# Enumerations
# ============================================================================

class FirmwareType(Enum):
    """Firmware component types."""
    DSP = "dsp"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    BIOS = "bios"


class DeviceType(Enum):
    """Device types."""
    NETWORKING = "NETWORKING"
    PHONE = "PHONE"
    PRINTER = "PRINTER"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FirmwareInfo:
    """
    Data class representing firmware/hardware component information.
    
    Attributes:
        name: Component name
        description: Detailed description
        type: Component type (dsp, hardware, software, etc.)
        version: Version string
        manufacturer: Manufacturer name
    """
    name: str
    description: str
    type: str
    version: str
    manufacturer: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for device registration."""
        return {
            "NAME": self.name,
            "DESCRIPTION": self.description,
            "TYPE": self.type,
            "VERSION": self.version,
            "MANUFACTURER": self.manufacturer
        }
    
    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.type})"
    
    def __repr__(self) -> str:
        return (f"FirmwareInfo(name='{self.name}', type='{self.type}', "
                f"version='{self.version}')")


@dataclass
class DeviceInfo:
    """
    Data class for comprehensive device information.
    
    Attributes:
        model: Device model
        serial: Serial number
        firmware: Main firmware version
        type: Device type
        manufacturer: Manufacturer name
        components: List of firmware/hardware components
    """
    model: Optional[str] = None
    serial: Optional[str] = None
    firmware: Optional[str] = None
    type: str = DeviceType.NETWORKING.value
    manufacturer: str = "Avaya"
    components: List[FirmwareInfo] = field(default_factory=list)
    
    def add_component(self, component: FirmwareInfo) -> None:
        """Add a firmware/hardware component."""
        self.components.append(component)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "model": self.model,
            "serial": self.serial,
            "firmware": self.firmware,
            "type": self.type,
            "manufacturer": self.manufacturer,
            "components": [c.to_dict() for c in self.components]
        }


# ============================================================================
# Main Avaya Support Class
# ============================================================================

class Avaya(MibSupportTemplate):
    """
    Enhanced SNMP MIB support for Avaya J100 series IP phones.
    
    This class extends MibSupportTemplate to provide comprehensive inventory
    support for Avaya J100 IP phones, including firmware, hardware, and
    software component detection.
    """
    
    MANUFACTURER = "Avaya"
    
    def __init__(self, *args, **kwargs):
        """Initialize Avaya support instance."""
        super().__init__(*args, **kwargs)
        self._cached_model: Optional[str] = None
        self._device_info: Optional[DeviceInfo] = None
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    # ========================================================================
    # Core Methods (Interface Implementation)
    # ========================================================================
    
    def get_type(self) -> str:
        """
        Get device type.
        
        Returns:
            Device type identifier (NETWORKING for IP phones)
        """
        return DeviceType.NETWORKING.value
    
    def get_manufacturer(self) -> str:
        """
        Get manufacturer name.
        
        Returns:
            Manufacturer name
        """
        return self.MANUFACTURER
    
    def get_firmware(self) -> Optional[str]:
        """
        Get main firmware version.
        
        Returns:
            Firmware version string or None if not available
        """
        try:
            firmware = self.get(ENDPT_APPINUSE)
            canonical = get_canonical_string(firmware)
            
            if canonical:
                logger.debug(f"Retrieved firmware version: {canonical}")
            else:
                logger.warning("Firmware version not available")
            
            return canonical
        except Exception as e:
            logger.error(f"Error retrieving firmware version: {e}")
            return None
    
    def get_model(self) -> Optional[str]:
        """
        Get device model.
        
        Returns from device object if available, otherwise queries SNMP.
        Caches result for performance.
        
        Returns:
            Model name or None if not available
        """
        if self._cached_model:
            return self._cached_model
        
        try:
            device = getattr(self, 'device', None)
            
            # Try to get from device object first
            if device:
                model_from_device = device.get('MODEL') if hasattr(device, 'get') else None
                if model_from_device:
                    self._cached_model = model_from_device
                    logger.debug(f"Retrieved model from device: {model_from_device}")
                    return model_from_device
            
            # Fall back to SNMP query
            model = get_canonical_string(self.get(ENDPT_MODEL))
            if model:
                self._cached_model = model
                logger.debug(f"Retrieved model from SNMP: {model}")
            else:
                logger.warning("Model information not available")
            
            return model
        except Exception as e:
            logger.error(f"Error retrieving model: {e}")
            return None
    
    def get_serial(self) -> Optional[str]:
        """
        Get device serial number.
        
        Returns:
            Serial number or None if not available
        """
        try:
            serial = get_canonical_string(self.get(ENDPT_PHONESN))
            
            if serial:
                logger.debug(f"Retrieved serial number: {serial}")
            else:
                logger.warning("Serial number not available")
            
            return serial
        except Exception as e:
            logger.error(f"Error retrieving serial number: {e}")
            return None
    
    # ========================================================================
    # Extended Methods
    # ========================================================================
    
    def get_dsp_version(self) -> Optional[str]:
        """
        Get DSP firmware version.
        
        Returns:
            DSP version string or None if not available
        """
        try:
            return get_canonical_string(self.get(ENDPT_DSPVERSION))
        except Exception as e:
            logger.error(f"Error retrieving DSP version: {e}")
            return None
    
    def get_hardware_version(self) -> Optional[str]:
        """
        Get hardware version.
        
        Returns:
            Hardware version string or None if not available
        """
        try:
            return get_canonical_string(self.get(ENDPT_HWVER))
        except Exception as e:
            logger.error(f"Error retrieving hardware version: {e}")
            return None
    
    def get_openssl_version(self) -> Optional[str]:
        """
        Get OpenSSL version.
        
        Returns:
            OpenSSL version string or None if not available
        """
        try:
            return get_canonical_string(self.get(ENDPT_OPENSSL_VERSION))
        except Exception as e:
            logger.error(f"Error retrieving OpenSSL version: {e}")
            return None
    
    def get_openssh_version(self) -> Optional[str]:
        """
        Get OpenSSH version.
        
        Returns:
            OpenSSH version string or None if not available
        """
        try:
            return get_canonical_string(self.get(ENDPT_OPENSSH_VERSION))
        except Exception as e:
            logger.error(f"Error retrieving OpenSSH version: {e}")
            return None
    
    def get_device_info(self) -> DeviceInfo:
        """
        Get comprehensive device information.
        
        Returns:
            DeviceInfo object containing all available device data
        """
        if self._device_info:
            return self._device_info
        
        info = DeviceInfo(
            model=self.get_model(),
            serial=self.get_serial(),
            firmware=self.get_firmware(),
            type=self.get_type(),
            manufacturer=self.get_manufacturer()
        )
        
        self._device_info = info
        return info
    
    # ========================================================================
    # Main Inventory Method
    # ========================================================================
    
    def run(self) -> bool:
        """
        Run inventory process to collect firmware and hardware information.
        
        Collects:
        - DSP firmware version
        - Hardware version
        - OpenSSL version
        - OpenSSH version
        
        Returns:
            True if inventory completed successfully, False otherwise
        """
        device = getattr(self, 'device', None)
        if not device:
            logger.error("No device object available for inventory")
            return False
        
        model = self.get_model()
        if not model:
            logger.warning("Model information not available, using generic name")
            model = "Avaya Phone"
        
        success_count = 0
        components_to_check = [
            (self.get_dsp_version, "DSP firmware", FirmwareType.DSP,
             "DSP firmware version"),
            (self.get_hardware_version, "Hardware", FirmwareType.HARDWARE,
             "Hardware version"),
            (self.get_openssl_version, "OpenSSL", FirmwareType.SOFTWARE,
             "OpenSSL version"),
            (self.get_openssh_version, "OpenSSH", FirmwareType.SOFTWARE,
             "OpenSSH version"),
        ]
        
        try:
            for getter_func, name, fw_type, description in components_to_check:
                version = getter_func()
                
                if not empty(version):
                    firmware_info = FirmwareInfo(
                        name=f"{model} {name}",
                        description=description,
                        type=fw_type.value,
                        version=version,
                        manufacturer=self.MANUFACTURER
                    )
                    
                    # Add to device (legacy dict format for compatibility)
                    if hasattr(device, 'add_firmware'):
                        device.add_firmware(firmware_info.to_dict())
                        logger.info(f"Added {name}: {version}")
                        success_count += 1
                    else:
                        logger.error(f"Device object does not support add_firmware method")
                else:
                    logger.debug(f"{name} version not available")
            
            if success_count > 0:
                logger.info(f"Successfully collected {success_count} component(s)")
                return True
            else:
                logger.warning("No firmware/hardware components were collected")
                return False
                
        except Exception as e:
            logger.error(f"Error during inventory run: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def validate_device(self) -> bool:
        """
        Validate that the device has minimum required information.
        
        Returns:
            True if device has at least serial or model, False otherwise
        """
        serial = self.get_serial()
        model = self.get_model()
        
        if not serial and not model:
            logger.warning("Device validation failed: no serial or model")
            return False
        
        logger.debug("Device validation passed")
        return True
    
    def get_all_versions(self) -> Dict[str, Optional[str]]:
        """
        Get all available version information.
        
        Returns:
            Dictionary with all version data
        """
        return {
            "firmware": self.get_firmware(),
            "dsp": self.get_dsp_version(),
            "hardware": self.get_hardware_version(),
            "openssl": self.get_openssl_version(),
            "openssh": self.get_openssh_version(),
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Avaya(model={self.get_model()}, "
                f"serial={self.get_serial()}, "
                f"firmware={self.get_firmware()})")
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        model = self.get_model() or "Unknown Model"
        serial = self.get_serial() or "No Serial"
        return f"{self.MANUFACTURER} {model} (S/N: {serial})"


# ============================================================================
# Module-level functions
# ============================================================================

def get_supported_oids() -> List[str]:
    """
    Get list of all OIDs supported by this module.
    
    Returns:
        List of OID strings
    """
    return [
        ENDPT_APPINUSE,
        ENDPT_DSPVERSION,
        ENDPT_MODEL,
        ENDPT_PHONESN,
        ENDPT_HWVER,
        ENDPT_OPENSSL_VERSION,
        ENDPT_OPENSSH_VERSION,
    ]


def get_mib_info() -> Dict[str, Any]:
    """
    Get MIB support information.
    
    Returns:
        Dictionary containing MIB metadata
    """
    return {
        "name": "avaya-j100-ipphone",
        "manufacturer": "Avaya",
        "device_type": "IP Phone",
        "series": "J100",
        "supported_oids": get_supported_oids(),
        "mib_support": mib_support
    }

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device class for testing
    class MockDevice:
        def add_firmware(self, fw):
            print(f"Added firmware: {fw}")

    # Test instantiation
    avaya = Avaya()
    avaya.device = MockDevice()
    print("Manufacturer:", avaya.get_manufacturer())
    print("Serial:", avaya.get_serial())
    print("Firmware:", avaya.get_firmware())
    print("Model:", avaya.get_model())
    print("All versions:", avaya.get_all_versions())
    print("Device info:", avaya.get_device_info().to_dict())
    print("Run result:", avaya.run())
    print("Validation:", avaya.validate_device())
    print("MIB info:", get_mib_info())
    print("Supported OIDs:", get_supported_oids())
    print("Module loaded and run successfully without errors.")

"""
Avaya J100 IP Phone SNMP MIB Support Module

This module provides enhanced inventory support for Avaya J100 series IP phones
using SNMP data from the Avaya-J100IpPhone-MIB.

Features:
- Firmware version detection (DSP, OpenSSL, OpenSSH)
- Hardware version tracking
- Model and serial number retrieval
- Comprehensive error handling and logging
- Type-safe implementations
"""
