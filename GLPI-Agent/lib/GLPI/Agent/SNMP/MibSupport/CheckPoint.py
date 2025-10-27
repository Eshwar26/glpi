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
            '.1.3.6.1.4.1.2620.1.6.1.0': 'SVN Foundation',  # svnProdName
            '.1.3.6.1.4.1.2620.1.6.2.0': 'R80',  # svnProdVerMajor
            '.1.3.6.1.4.1.2620.1.6.3.0': '10',  # svnProdVerMinor
            '.1.3.6.1.4.1.2620.1.6.4.1.0': '1.2.3',  # svnVersion
            '.1.3.6.1.4.1.2620.1.6.4.2.0': '456',  # svnBuild
            '.1.3.6.1.4.1.2620.1.6.5.1.0': 'Gaia Embedded',  # osName
            '.1.3.6.1.4.1.2620.1.6.5.2.0': 'R80',  # osMajorVer
            '.1.3.6.1.4.1.2620.1.6.5.3.0': '10',  # osMinorVer
            '.1.3.6.1.4.1.2620.1.6.16.3.0': 'SN123456789',  # svnApplianceSerialNumber
            '.1.3.6.1.4.1.2620.1.6.16.7.0': 'Check Point 1540',  # svnApplianceModel
            '.1.3.6.1.4.1.2620.1.6.16.9.0': 'Check Point',  # svnApplianceManufacturer
        }
        return mock_values.get(oid, None)

# Mock Device class for compatibility
class Device:
    def __init__(self):
        self.firmwares = []  # To store added firmwares

    def add_firmware(self, fw_dict):
        self.firmwares.append(fw_dict)
        print(f"Added firmware: {fw_dict}")

# Constants
CHECKPOINT = '.1.3.6.1.4.1.2620'

SVN = CHECKPOINT + '.1.6'

SVN_PROD_NAME = SVN + '.1.0'
SVN_PROD_VER_MAJOR = SVN + '.2.0'
SVN_PROD_VER_MINOR = SVN + '.3.0'
SVN_INFO = SVN + '.4'
SVN_OS_INFO = SVN + '.5'
SVN_APPLIANCE_INFO = SVN + '.16'

SVN_VERSION = SVN_INFO + '.1.0'
SVN_BUILD = SVN_INFO + '.2.0'

OS_NAME = SVN_OS_INFO + '.1.0'
OS_MAJOR_VER = SVN_OS_INFO + '.2.0'
OS_MINOR_VER = SVN_OS_INFO + '.3.0'

SVN_APPLIANCE_SERIAL_NUMBER = SVN_APPLIANCE_INFO + '.3.0'
SVN_APPLIANCE_MODEL = SVN_APPLIANCE_INFO + '.7.0'
SVN_APPLIANCE_MANUFACTURER = SVN_APPLIANCE_INFO + '.9.0'

mib_support = [
    {
        'name': 'CheckPoint',
        'sysobjectid': get_regexp_oid_match(CHECKPOINT)
    }
]

class CheckPoint(MibSupportTemplate):
    def get_firmware(self):
        version = self.get(SVN_VERSION)
        build = self.get(SVN_BUILD)
        if version and build:
            return get_canonical_string(f"{version} (build {build})")
        return None

    def get_serial(self):
        return get_canonical_string(self.get(SVN_APPLIANCE_SERIAL_NUMBER))

    def get_manufacturer(self):
        return get_canonical_string(self.get(SVN_APPLIANCE_MANUFACTURER))

    def get_model(self):
        return get_canonical_string(self.get(SVN_APPLIANCE_MODEL))

    def run(self):
        device = self.device
        if not device:
            return

        manufacturer = self.get_manufacturer()
        if not manufacturer:
            return

        svn_prod_ver_major = self.get(SVN_PROD_VER_MAJOR)
        if svn_prod_ver_major is not None:
            prod_name = get_canonical_string(self.get(SVN_PROD_NAME))
            prod_minor = get_canonical_string(self.get(SVN_PROD_VER_MINOR))
            version = f"{svn_prod_ver_major}.{prod_minor}"
            fw_dict = {
                'NAME': prod_name,
                'DESCRIPTION': f"{manufacturer} SVN version",
                'TYPE': 'system',
                'VERSION': version,
                'MANUFACTURER': manufacturer
            }
            device.add_firmware(fw_dict)

        os_major_ver = self.get(OS_MAJOR_VER)
        if os_major_ver is not None:
            os_name = get_canonical_string(self.get(OS_NAME))
            os_minor = get_canonical_string(self.get(OS_MINOR_VER))
            version = f"{os_major_ver}.{os_minor}"
            fw_dict = {
                'NAME': os_name,
                'DESCRIPTION': f"{manufacturer} OS version",
                'TYPE': 'system',
                'VERSION': version,
                'MANUFACTURER': manufacturer
            }
            device.add_firmware(fw_dict)

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Test instantiation
    checkpoint = CheckPoint()
    checkpoint.device = Device()
    print("Firmware:", checkpoint.get_firmware())
    print("Serial:", checkpoint.get_serial())
    print("Manufacturer:", checkpoint.get_manufacturer())
    print("Model:", checkpoint.get_model())
    print("Before run - Firmwares:", len(checkpoint.device.firmwares))
    checkpoint.run()
    print("After run - Firmwares:", len(checkpoint.device.firmwares))
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::CheckPoint - Inventory module for CheckPoint appliance

This module enhances CheckPoint appliances support.
"""
