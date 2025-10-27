import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

def get_canonical_mac_address(value):
    """Mock implementation of getCanonicalMacAddress: Formats MAC address."""
    if not value:
        return None
    # Assuming value is a hex string like '001122334455'
    if len(value) != 12:
        return None
    try:
        mac = ':'.join(value[i:i+2] for i in range(0, 12, 2)).upper()
        return mac
    except Exception:
        return None

def empty(value):
    return value is None or str(value).strip() == ''

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.4.1.674.10895.3000.1.2.100.1.0': 'Dell Networking N3000 Series',  # productIdentificationDisplayName
            '.1.3.6.1.4.1.674.10895.3000.1.2.100.3.0': 'Dell',  # productIdentificationVendor
            '.1.3.6.1.4.1.674.10895.3000.1.2.100.4.0': '9.10(0.0)',  # productIdentificationVersion
            '.1.3.6.1.4.1.674.10895.3000.1.2.100.8.1.2.1': 'SN123456789',  # productIdentificationSerialNumber
            '.1.3.6.1.4.1.674.10895.3000.1.2.100.8.1.3.1': 'Asset123',  # productIdentificationAssetTag
            '.1.3.6.1.4.1.674.10895.3000.1.2.100.8.1.4.1': 'Service123',  # productIdentificationServiceTag
            '.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.3.1': '001A1E000101',  # os10ChassisMacAddr
            '.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.5.1': 'PPID123',  # os10ChassisPPID
            '.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.7.1': 'Service456',  # os10ChassisServiceTag
        }
        return mock_values.get(oid, None)

# Constants
ENTERPRISES = '.1.3.6.1.4.1'
DELL = ENTERPRISES + '.674'

POWER_CONNECT_VENDOR_MIB = DELL + '.10895.3000'
HARDWARE = POWER_CONNECT_VENDOR_MIB + '.1.2'
PRODUCT_IDENTIFICATION = HARDWARE + ".100"

PRODUCT_IDENTIFICATION_DISPLAY_NAME = PRODUCT_IDENTIFICATION + ".1.0"
PRODUCT_IDENTIFICATION_VENDOR = PRODUCT_IDENTIFICATION + ".3.0"
PRODUCT_IDENTIFICATION_VERSION = PRODUCT_IDENTIFICATION + ".4.0"
PRODUCT_IDENTIFICATION_SERIAL_NUMBER = PRODUCT_IDENTIFICATION + ".8.1.2.1"
PRODUCT_IDENTIFICATION_ASSET_TAG = PRODUCT_IDENTIFICATION + ".8.1.3.1"
PRODUCT_IDENTIFICATION_SERVICE_TAG = PRODUCT_IDENTIFICATION + ".8.1.4.1"

OS10 = DELL + '.11000.5000.100'
OS10_PRODUCTS = OS10 + '.2'

OS10_CHASSIS_MIB = OS10 + '.4'
OS10_CHASSIS_OBJECT = OS10_CHASSIS_MIB + '.1.1'
OS10_CHASSIS_MAC_ADDR = OS10_CHASSIS_OBJECT + '.3.1.3.1'
OS10_CHASSIS_PPID = OS10_CHASSIS_OBJECT + '.3.1.5.1'
OS10_CHASSIS_SERVICE_TAG = OS10_CHASSIS_OBJECT + '.3.1.7.1'

mib_support = [
    {
        'name': 'dell-powerconnect',
        'oid': POWER_CONNECT_VENDOR_MIB
    },
    {
        'name': 'dell-os10-product',
        'sysobjectid': get_regexp_oid_match(OS10_PRODUCTS)
    }
]

class Dell(MibSupportTemplate):
    def get_type(self):
        return 'NETWORKING'

    def get_firmware(self):
        return get_canonical_string(self.get(PRODUCT_IDENTIFICATION_VERSION))

    def get_manufacturer(self):
        device = self.device
        if not device:
            return None

        if device.get('MANUFACTURER'):
            return None

        vendor = get_canonical_string(self.get(PRODUCT_IDENTIFICATION_VENDOR))
        return vendor or 'Dell'

    def get_serial(self):
        serial = get_canonical_string(self.get(PRODUCT_IDENTIFICATION_SERIAL_NUMBER))
        if serial:
            return serial
        return get_canonical_string(self.get(OS10_CHASSIS_PPID))

    def get_mac_address(self):
        device = self.device
        if not device:
            return None

        if device.get('MAC'):
            return None

        return get_canonical_mac_address(self.get(OS10_CHASSIS_MAC_ADDR))

    def get_model(self):
        device = self.device
        if not device:
            return None

        if device.get('MODEL'):
            return None

        return get_canonical_string(self.get(PRODUCT_IDENTIFICATION_DISPLAY_NAME))

    def run(self):
        device = self.device
        if not device:
            return

        assettag = get_canonical_string(self.get(PRODUCT_IDENTIFICATION_ASSET_TAG))
        if empty(assettag) or assettag.lower() == 'none':
            servicetag = get_canonical_string(self.get(PRODUCT_IDENTIFICATION_SERVICE_TAG)) or get_canonical_string(self.get(OS10_CHASSIS_SERVICE_TAG))
            if not empty(servicetag) and servicetag.lower() != 'none':
                assettag = servicetag

        if not empty(assettag):
            if 'INFO' not in device:
                device['INFO'] = {}
            device['INFO']['ASSETTAG'] = assettag

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device dict for testing
    device = {
        'MANUFACTURER': None,
        'MAC': None,
        'MODEL': None,
        'INFO': {}
    }

    # Test instantiation
    dell = Dell()
    dell.device = device
    print("Type:", dell.get_type())
    print("Firmware:", dell.get_firmware())
    print("Manufacturer:", dell.get_manufacturer())
    print("Serial:", dell.get_serial())
    print("MAC Address:", dell.get_mac_address())
    print("Model:", dell.get_model())
    print("Before run - INFO:", device.get('INFO', {}))
    dell.run()
    print("After run - INFO:", device.get('INFO', {}))
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Dell - Inventory module for Dell PowerConnect switches

The module enhances support for Dell devices
"""
