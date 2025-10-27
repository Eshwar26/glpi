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
            '.1.3.6.1.4.1.1991.1.1.1.1.2.0': 'SN123456789',
            '.1.3.6.1.4.1.1991.1.1.2.1.11.0': 'FW 8.2.1'
        }
        return mock_values.get(oid, None)

# Brocade constants
BROCade = '.1.3.6.1.4.1.1991'
SERIAL = BROCade + '.1.1.1.1.2.0'
FW_PRI = BROCade + '.1.1.2.1.11.0'

mib_support = [
    {
        'name': 'brocade-switch',
        'sysobjectid': get_regexp_oid_match(BROCade)
    }
]

class Brocade(MibSupportTemplate):
    def get_serial(self):
        return self.get(SERIAL)

    def get_firmware(self):
        return self.get(FW_PRI)

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    brocade = Brocade()
    print("Serial:", brocade.get_serial())
    print("Firmware:", brocade.get_firmware())
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Brocade - Inventory module for Brocade Switches

The module enhances Brocade Switches devices support.
"""
