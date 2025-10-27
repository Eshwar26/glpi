import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_regexp_oid_match(oid):
    # Returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

def get_canonical_string(value):
    # Mock function to get canonical string representation
    # In real implementation, this would handle string normalization
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
            '.1.3.6.1.4.1.11.2.36.1.1.2.6.0': 'K.15.18.0014',  # hpHttpMgVersion
            '.1.3.6.1.4.1.11.2.36.1.1.2.8.0': 'K.15.18',  # hpHttpMgROMVersion
            '.1.3.6.1.4.1.11.2.36.1.1.2.9.0': 'SG35PCN0B8',  # hpHttpMgSerialNumber
        }
        return mock_values.get(oid, None)

# Mock Device class with addFirmware method
class MockDevice:
    def __init__(self):
        self.firmwares = []
    
    def addFirmware(self, firmware_info):
        self.firmwares.append(firmware_info)

# Constants
# See HP-ICF-OID
HP_ETHER_SWITCH = '.1.3.6.1.4.1.11.2.3.7.11'

# See HP-HTTP-MG/SEMI
HP_WEB_MGMT = '.1.3.6.1.4.1.11.2.36'
HP_HTTP_MG_NET_CITIZEN = HP_WEB_MGMT + '.1.1.2'
HP_HTTP_MG_VERSION = HP_HTTP_MG_NET_CITIZEN + '.6.0'
HP_HTTP_MG_ROM_VERSION = HP_HTTP_MG_NET_CITIZEN + '.8.0'
HP_HTTP_MG_SERIAL_NUMBER = HP_HTTP_MG_NET_CITIZEN + '.9.0'

mib_support = [
    {
        'name': 'hp-etherswitch',
        'sysobjectid': get_regexp_oid_match(HP_ETHER_SWITCH)
    }
]

class HPHttpManagement(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_firmware(self):
        return get_canonical_string(self.get(HP_HTTP_MG_ROM_VERSION))
    
    def get_serial(self):
        return self.get(HP_HTTP_MG_SERIAL_NUMBER)
    
    def run(self):
        device = self.device
        if not device:
            return
        
        hp_http_mg_version = self.get(HP_HTTP_MG_VERSION)
        if not hp_http_mg_version:
            return
        
        device.addFirmware({
            'NAME': 'HP-HttpMg-Version',
            'DESCRIPTION': "HP Web Management Software version",
            'TYPE': "system",
            'VERSION': get_canonical_string(hp_http_mg_version),
            'MANUFACTURER': "HP"
        })

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    hp_http_mgmt = HPHttpManagement()
    print("Firmware:", hp_http_mgmt.get_firmware())
    print("Serial:", hp_http_mgmt.get_serial())
    
    # Mock device for run
    hp_http_mgmt.device = MockDevice()
    print("\nBefore run - Firmwares:", hp_http_mgmt.device.firmwares)
    hp_http_mgmt.run()
    print("After run - Firmwares:")
    for fw in hp_http_mgmt.device.firmwares:
        print(f"  - {fw['NAME']}: {fw['VERSION']}")
        print(f"    Description: {fw['DESCRIPTION']}")
        print(f"    Type: {fw['TYPE']}, Manufacturer: {fw['MANUFACTURER']}")
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::HPHttpManagement - Inventory module for HP switches with HTTP management

This module enhances HP switches devices support.
"""
