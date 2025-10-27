import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

def get_canonical_serial_number(value):
    if value is None:
        return None
    return str(value).strip().upper()

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
            '.1.3.6.1.3.94.1.6.1.1.1': 'EMC Unit 1',  # connUnitSn .1
            '.1.3.6.1.3.94.1.6.1.7.1': 'EMC Model X',  # connUnitProduct .1
        }
        return mock_values.get(oid, None)

    def walk(self, oid):
        # Mock SNMP walk; returns dict of index: value
        if oid == '.1.3.6.1.3.94.1.6.1.1':  # connUnitId
            return {'1': '1'}  # Mock single unit with id 1
        return {}

# Constants
EMC = '.1.3.6.1.4.1.674'

EXPERIMENTAL = '.1.3.6.1.3'
FCMGMT = EXPERIMENTAL + '.94'

CONN_UNIT_TABLE = FCMGMT + '.1.6'
CONN_UNIT_ENTRY = CONN_UNIT_TABLE + '.1'
CONN_UNIT_ID = CONN_UNIT_ENTRY + '.1'
CONN_UNIT_PRODUCT = CONN_UNIT_ENTRY + '.7'
CONN_UNIT_SN = CONN_UNIT_ENTRY + '.8'

mib_support = [
    {
        'name': 'emc',
        'sysobjectid': get_regexp_oid_match(EMC)
    }
]

class EMC(MibSupportTemplate):
    def get_type(self):
        # Only set type if we match storage experimental OID, we don't want to reset
        # Dell printers type by mistake
        conn_unit_id = self.walk(CONN_UNIT_ID)
        if not conn_unit_id:
            return None

        return 'NETWORKING'

    def get_serial(self):
        conn_unit_id = self.walk(CONN_UNIT_ID)
        if not conn_unit_id:
            return None

        unit_id = sorted(conn_unit_id.keys())[0] if conn_unit_id else None
        if not unit_id:
            return None

        return get_canonical_serial_number(self.get(CONN_UNIT_SN + f".{unit_id}"))

    def get_model(self):
        conn_unit_id = self.walk(CONN_UNIT_ID)
        if not conn_unit_id:
            return None

        unit_id = sorted(conn_unit_id.keys())[0] if conn_unit_id else None
        if not unit_id:
            return None

        return get_canonical_string(self.get(CONN_UNIT_PRODUCT + f".{unit_id}"))

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    emc = EMC()
    print("Type:", emc.get_type())
    print("Serial:", emc.get_serial())
    print("Model:", emc.get_model())
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::EMC - Inventory module for EMC devices

The module enhances EMC devices support.
"""
