import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

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
            '.1.3.6.1.4.1.9.2.1.3.0': 'cisco-router-01',  # hostName
        }
        return mock_values.get(oid, None)

# Mock Device class for compatibility, including get_first method
class Device:
    def __init__(self):
        pass  # Can hold data if needed

    def get_first(self, oid):
        # Mock get_first: simulates walking the OID table and returning first value
        # For entPhysicalModelName, mock as if walking .1.3.6.1.2.1.47.1.1.1.1.13 returns a dict
        if oid == '.1.3.6.1.2.1.47.1.1.1.1.13':
            # Mock walk result: {'1': 'Cisco ISR 4331', '2': None, '3': 'Module XYZ'}
            mock_walk = {'1': 'Cisco ISR 4331'}
            for index, value in mock_walk.items():
                if value:
                    return value
        return None

# Constants
PRIORITY = 5

ENT_PHYSICAL_MODEL_NAME = '.1.3.6.1.2.1.47.1.1.1.1.13'

CISCO = '.1.3.6.1.4.1.9'
CISCO_LOCAL = CISCO + '.2'

HOST_NAME = CISCO_LOCAL + '.1.3.0'

mib_support = [
    {
        'name': 'cisco',
        'sysobjectid': get_regexp_oid_match(CISCO)
    }
]

class Cisco(MibSupportTemplate):
    def get_model(self):
        device = self.device
        if not device:
            return None
        return get_canonical_string(device.get_first(ENT_PHYSICAL_MODEL_NAME))

    def get_snmp_hostname(self):
        return get_canonical_string(self.get(HOST_NAME))

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    cisco = Cisco()
    cisco.device = Device()
    print("Model:", cisco.get_model())
    print("SNMP Hostname:", cisco.get_snmp_hostname())
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Cisco - Inventory module to enhance Cisco devices support.

The module enhances Cisco support.
"""

