import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

def empty(value):
    return value is None or str(value).strip() == ''

def is_integer(value):
    if value is None:
        return False
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

def get_regexp_oid_match(oid):
    # Assuming it returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns None to avoid errors
        return None

# NETTRACK-E3METER-SNMP-MIB
NETTRACK = '.1.3.6.1.4.1.21695'

PUBLIC = NETTRACK + '.1'

E3_IPM = PUBLIC + '.10.7'

E3_IPM_INFO_SERIAL = E3_IPM + '.1.1'
E3_IPM_INFO_HW_VERSION = E3_IPM + '.1.3'
E3_IPM_INFO_FW_VERSION = E3_IPM + '.1.4'

mib_support = [
    {
        'name': 'bachmann-pdu',
        'sysobjectid': get_regexp_oid_match(PUBLIC)
    }
]

class Bachmann(MibSupportTemplate):
    def get_manufacturer(self):
        return 'Bachmann'

    def get_serial(self):
        return get_canonical_string(self.get(E3_IPM_INFO_SERIAL))

    def get_firmware(self):
        fwrev = self.get(E3_IPM_INFO_FW_VERSION)
        if not fwrev:
            return None
        if not is_integer(fwrev):
            return None

        fwrev = int(fwrev)
        major = fwrev // 256
        minor = fwrev % 256

        return f"{major}.{minor}"

    def run(self):
        device = self.device
        if not device:
            return

        # Handle hardware revision if found
        hwversion = self.get(E3_IPM_INFO_HW_VERSION)
        if not empty(hwversion) and is_integer(hwversion):
            hw_revision = {
                'NAME': 'Hardware version',
                'DESCRIPTION': 'Pdu hardware revision',
                'TYPE': 'hardware',
                'VERSION': hwversion,
                'MANUFACTURER': 'Bachmann'
            }

            device.add_firmware(hw_revision)


# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device class for testing
    class MockDevice:
        def add_firmware(self, fw):
            print(f"Added firmware: {fw}")

    # Test instantiation
    bach = Bachmann()
    bach.device = MockDevice()
    bach.run()
    print("Manufacturer:", bach.get_manufacturer())
    print("Serial:", bach.get_serial())
    print("Firmware:", bach.get_firmware())
    print("Module loaded and run successfully without errors.")
