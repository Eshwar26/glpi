import re

# Mock or simple implementations for GLPI Agent functions/tools
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
            '.1.3.6.1.4.1.534.6.6.7.1.2.1.4.0': 'SN123456789',  # serial
            '.1.3.6.1.4.1.534.6.6.7.1.2.1.3.0': 'ePDU Model X',  # model
            '.1.3.6.1.4.1.534.6.6.7.1.2.1.5.0': 'FW 2.3.1',  # firmware
        }
        return mock_values.get(oid, None)

# Constants
EPDU = '.1.3.6.1.4.1.534.6.6.7'

MODEL = EPDU + '.1.2.1.3.0'
SERIAL = EPDU + '.1.2.1.4.0'
FIRMWARE = EPDU + '.1.2.1.5.0'

mib_support = [
    {
        'name': 'eaton-epdu',
        'sysobjectid': get_regexp_oid_match(EPDU)
    }
]

class EatonEpdu(MibSupportTemplate):
    def get_serial(self):
        return self.get(SERIAL)

    def get_model(self):
        return self.get(MODEL)

    def get_firmware(self):
        return self.get(FIRMWARE)

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    epdu = EatonEpdu()
    print("Serial:", epdu.get_serial())
    print("Model:", epdu.get_model())
    print("Firmware:", epdu.get_firmware())
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::EatonEpdu - Inventory module for Eaton ePDUs

The module enhances Eaton ePDU devices support.
"""
