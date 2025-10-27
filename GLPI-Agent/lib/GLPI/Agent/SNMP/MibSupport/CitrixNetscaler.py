import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.4.1.9.9.719.1.9.6.1.6.1': 'UCSB-240-M3',  # cucsComputeBoardModel
            '.1.3.6.1.4.1.9.9.719.1.9.6.1.14.1': 'SN123456789',  # cucsComputeBoardSerial
        }
        return mock_values.get(oid, None)

# Constants
PRIORITY = 5

CISCO = '.1.3.6.1.4.1.9'
CISCO_MGMT = CISCO + '.9'

CISCO_UNIFIED_COMPUTING_MIB = CISCO_MGMT + '.719'
CISCO_UNIFIED_COMPUTING_MIB_OBJECTS = CISCO_UNIFIED_COMPUTING_MIB + '.1'

CUCS_COMPUTE_OBJECTS = CISCO_UNIFIED_COMPUTING_MIB_OBJECTS + '.9'
CUCS_COMPUTE_BOARD_TABLE = CUCS_COMPUTE_OBJECTS + '.6'
CUCS_COMPUTE_BOARD_DN = CUCS_COMPUTE_BOARD_TABLE + '.1.2.1'
CUCS_COMPUTE_BOARD_MODEL = CUCS_COMPUTE_BOARD_TABLE + '.1.6.1'
CUCS_COMPUTE_BOARD_SERIAL = CUCS_COMPUTE_BOARD_TABLE + '.1.14.1'

mib_support = [
    {
        'name': 'cisco-ucs-board',
        'privateoid': CUCS_COMPUTE_BOARD_DN,
    }
]

class CiscoUcsBoard(MibSupportTemplate):
    def get_model(self):
        return get_canonical_string(self.get(CUCS_COMPUTE_BOARD_MODEL))

    def get_serial(self):
        return get_canonical_string(self.get(CUCS_COMPUTE_BOARD_SERIAL))

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    ucs_board = CiscoUcsBoard()
    print("Model:", ucs_board.get_model())
    print("Serial:", ucs_board.get_serial())
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::CiscoUcsBoard - Inventory module to support Cisco UCS board.

The module enhances Cisco support.
"""
