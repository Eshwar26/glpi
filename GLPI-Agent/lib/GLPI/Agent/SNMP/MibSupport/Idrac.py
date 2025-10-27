import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_regexp_oid_match(oid):
    # Returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked
    
    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.4.1.674.10892.2.1.1.11.0': 'ABCD1234',  # serial
        }
        return mock_values.get(oid, None)

# Constants
IDRAC = '.1.3.6.1.4.1.674.10892'
SERIAL = IDRAC + '.2.1.1.11.0'

mib_support = [
    {
        'name': 'idrac',
        'sysobjectid': get_regexp_oid_match(IDRAC)
    }
]

class Idrac(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_serial(self):
        return self.get(SERIAL)

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    idrac = Idrac()
    print("Serial:", idrac.get_serial())
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Idrac - Inventory module for Idrac

This module enhances Idrac support.
"""
