import re

# Mock or simplified GLPI Agent helper functions
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

# Base mock class (acts like GLPI::Agent::SNMP::MibSupportTemplate)
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # Will be set externally

    def get(self, oid):
        """Mock SNMP GET — override or extend in tests"""
        mock_values = {
            '.1.3.6.1.4.1.1004849.2.1.1.1.0': 'v2.3.4',     # softwareRevision
            '.1.3.6.1.4.1.1004849.2.1.1.2.0': 'HW-Rev-A1',  # hardwareRevision
            '.1.3.6.1.4.1.1004849.2.1.2.4.0': 'SN12345678', # serialNumber
            '.1.3.6.1.4.1.1004849.2.1.2.5.0': 'SysV1.2',    # systemVersion
            '.1.3.6.1.4.1.1004849.2.1.2.6.0': 'Intelbras-IP-Camera',  # deviceType
        }
        return mock_values.get(oid, None)

# Mock Device class with firmware list
class MockDevice:
    def __init__(self):
        self.firmwares = []

    def add_firmware(self, fw):
        """Mimics $device->addFirmware() in Perl"""
        self.firmwares.append(fw)

# OID constants (following the DAHUA-SNMP-MIB mapping)
DAHUA = '.1.3.6.1.4.1.1004849'
SYSTEM_INFO = DAHUA + '.2.1'

SOFTWARE_REVISION = SYSTEM_INFO + '.1.1.0'
HARDWARE_REVISION = SYSTEM_INFO + '.1.2.0'
SERIAL_NUMBER = SYSTEM_INFO + '.2.4.0'
SYSTEM_VERSION = SYSTEM_INFO + '.2.5.0'
DEVICE_TYPE = SYSTEM_INFO + '.2.6.0'

# MIB support definition
mib_support = [
    {
        'name': 'intelbras',
        'oid': SYSTEM_INFO
    }
]

class Intelbras(MibSupportTemplate):
    """Equivalent to GLPI::Agent::SNMP::MibSupport::Intelbras"""

    def get_type(self):
        return 'NETWORKING'

    def get_manufacturer(self):
        return 'Intelbras'

    def get_serial(self):
        return get_canonical_string(self.get(SERIAL_NUMBER))

    def get_firmware(self):
        return get_canonical_string(self.get(SOFTWARE_REVISION))

    def get_model(self):
        return get_canonical_string(self.get(DEVICE_TYPE))

    def run(self):
        device = self.device
        if not device:
            return

        hardware_revision = get_canonical_string(self.get(HARDWARE_REVISION))
        if hardware_revision:
            firmware = {
                'NAME': 'Intelbras hardware',
                'DESCRIPTION': 'Hardware version',
                'TYPE': 'hardware',
                'VERSION': hardware_revision,
                'MANUFACTURER': 'Intelbras'
            }
            device.add_firmware(firmware)

        system_version = get_canonical_string(self.get(SYSTEM_VERSION))
        if system_version:
            firmware = {
                'NAME': 'Intelbras system',
                'DESCRIPTION': 'System version',
                'TYPE': 'system',
                'VERSION': system_version,
                'MANUFACTURER': 'Intelbras'
            }
            device.add_firmware(firmware)

# For standalone testing
if __name__ == "__main__":
    intelbras = Intelbras()
    intelbras.device = MockDevice()

    print("Type:", intelbras.get_type())
    print("Manufacturer:", intelbras.get_manufacturer())
    print("Serial:", intelbras.get_serial())
    print("Firmware:", intelbras.get_firmware())
    print("Model:", intelbras.get_model())

    print("\nBefore run - Firmwares:", intelbras.device.firmwares)
    intelbras.run()
    print("After run - Firmwares found:", len(intelbras.device.firmwares))

    for i, fw in enumerate(intelbras.device.firmwares, 1):
        print(f"\n  Firmware {i}:")
        for k, v in fw.items():
            print(f"    {k}: {v}")

    print("\nModule executed successfully with full functionality.")
    
