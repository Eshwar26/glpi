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

def get_regexp_oid_match(oid):
    # Assuming it returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.4.1.17420.1.2.4.0': 'FW 2.1.0',  # devVersion
            '.1.3.6.1.4.1.17420.1.2.3.0': '001A1E000101',  # devMAC
            '.1.3.6.1.4.1.17420.1.2.9.1.19.0': 'PDU-01',  # pdu01ModelNo
        }
        return mock_values.get(oid, None)

# Constants
ENTERPRISES = '.1.3.6.1.4.1'
DIGIPOWER = ENTERPRISES + '.17420'

DEV_MAC = DIGIPOWER + '.1.2.3.0'
DEV_VERSION = DIGIPOWER + '.1.2.4.0'

PDU01_MODEL_NO = DIGIPOWER + '.1.2.9.1.19.0'

mib_support = [
    {
        'name': 'digipower',
        'sysobjectid': get_regexp_oid_match(DIGIPOWER)
    }
]

class DigiPower(MibSupportTemplate):
    def get_firmware(self):
        return get_canonical_string(self.get(DEV_VERSION))

    def get_mac_address(self):
        device = self.device
        if not device:
            return None

        if device.get('MAC'):
            return None

        return get_canonical_mac_address(self.get(DEV_MAC))

    def get_model(self):
        return get_canonical_string(self.get(PDU01_MODEL_NO))

    def get_type(self):
        return 'NETWORKING'

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device dict for testing
    device = {'MAC': None}

    # Test instantiation
    digipower = DigiPower()
    digipower.device = device
    print("Firmware:", digipower.get_firmware())
    print("MAC Address:", digipower.get_mac_address())
    print("Model:", digipower.get_model())
    print("Type:", digipower.get_type())
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::DigiPower - Inventory module for Digipower devices

The module adds support for Digipower devices
"""
