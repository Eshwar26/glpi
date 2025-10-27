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
            '.1.3.6.1.4.1.11256.1.0.1.0': 'SN123456789',  # stormshield_model (exists, so StormShield)
            '.1.3.6.1.4.1.11256.1.0.2.0': 'FW 3.2.1',  # stormshield_fw_pri
            '.1.3.6.1.4.1.11256.1.0.3.0': 'SS-123456',  # stormshield_serial
            '.1.3.6.1.4.1.11256.1.0.4.0': 'StormShield Device Name',  # stormshield_name
        }
        return mock_values.get(oid, None)  # None if not StormShield

# Constants
FREEBSD = '.1.3.6.1.4.1.8072.3.2.8'
STORMSHIELD = '.1.3.6.1.4.1.11256'
STORMSHIELD_MODEL = STORMSHIELD + '.1.0.1.0'
STORMSHIELD_FW_PRI = STORMSHIELD + '.1.0.2.0'
STORMSHIELD_SERIAL = STORMSHIELD + '.1.0.3.0'
STORMSHIELD_NAME = STORMSHIELD + '.1.0.4.0'

mib_support = [
    {
        'name': 'FreeBSD',
        'sysobjectid': get_regexp_oid_match(FREEBSD)
    }
]

class FreeBSD(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._STORMSHIELD = None  # Cache for _is_stormshield

    def _is_stormshield(self):
        if self._STORMSHIELD is None:
            self._STORMSHIELD = bool(self.get(STORMSHIELD_MODEL))
        return self._STORMSHIELD

    def get_serial(self):
        if self._is_stormshield():
            return self.get(STORMSHIELD_SERIAL)
        return None

    def get_firmware(self):
        if self._is_stormshield():
            return self.get(STORMSHIELD_FW_PRI)
        return None

    def get_type(self):
        if self._is_stormshield():
            return 'NETWORKING'
        return None

    def get_model(self):
        if self._is_stormshield():
            return self.get(STORMSHIELD_MODEL)
        return None

    def get_manufacturer(self):
        if self._is_stormshield():
            return 'StormShield'
        return None

    def run(self):
        if self._is_stormshield():
            device = self.device
            if not device:
                return
            name = self.get(STORMSHIELD_NAME)
            if name:
                if 'INFO' not in device:
                    device['INFO'] = {}
                device['INFO']['NAME'] = name

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    freebsd = FreeBSD()
    print("Is StormShield:", freebsd._is_stormshield())
    print("Serial:", freebsd.get_serial())
    print("Firmware:", freebsd.get_firmware())
    print("Type:", freebsd.get_type())
    print("Model:", freebsd.get_model())
    print("Manufacturer:", freebsd.get_manufacturer())
    # Mock device for run
    freebsd.device = {'INFO': {}}
    print("Before run - INFO:", freebsd.device['INFO'])
    freebsd.run()
    print("After run - INFO:", freebsd.device['INFO'])
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::FreeBSD - Inventory module for FreeBSD

The module enhances FreeBSD devices support.
"""
