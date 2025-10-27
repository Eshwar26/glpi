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

def empty(value):
    # Check if value is empty or None
    return value is None or value == '' or (isinstance(value, str) and not value.strip())

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked
        self.priority = 1  # Default priority
    
    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.4.1.11.2.36.1.1.2.4.0': 'HP',  # hpHttpMgManufacturer
            '.1.3.6.1.4.1.11.2.36.1.1.2.5.0': 'StorageWorks MSA2000',  # hpHttpMgProduct
            '.1.3.6.1.4.1.11.2.36.1.1.2.6.0': 'T252P001',  # hpHttpMgVersion
            '.1.3.6.1.4.1.11.2.36.1.1.2.7.0': 'HW-v1.2',  # hpHttpMgHWVersion
            '.1.3.6.1.4.1.11.2.36.1.1.2.8.0': 'ROM-v2.5',  # hpHttpMgROMVersion
            '.1.3.6.1.4.1.11.2.36.1.1.2.9.0': '2M286B00GP',  # hpHttpMgSerialNumber
        }
        return mock_values.get(oid, None)

# Mock Device class with addFirmware method
class MockDevice:
    def __init__(self):
        self.firmwares = []
    
    def addFirmware(self, firmware_info):
        self.firmwares.append(firmware_info)

# Constants
PRIORITY = 8

HP_CITIZEN = '.1.3.6.1.4.1.11.10'

# See SEMI-MIB
HP_HTTP_MG_MOD = '.1.3.6.1.4.1.11.2.36.1'

HP_HTTP_MG_NET_CITIZEN = HP_HTTP_MG_MOD + '.1.2'

HP_HTTP_MG_MANUFACTURER = HP_HTTP_MG_NET_CITIZEN + '.4.0'
HP_HTTP_MG_PRODUCT = HP_HTTP_MG_NET_CITIZEN + '.5.0'
HP_HTTP_MG_VERSION = HP_HTTP_MG_NET_CITIZEN + '.6.0'
HP_HTTP_MG_HW_VERSION = HP_HTTP_MG_NET_CITIZEN + '.7.0'
HP_HTTP_MG_ROM_VERSION = HP_HTTP_MG_NET_CITIZEN + '.8.0'
HP_HTTP_MG_SERIAL_NUMBER = HP_HTTP_MG_NET_CITIZEN + '.9.0'

mib_support = [
    {
        'name': 'hp-citizen',
        'sysobjectid': get_regexp_oid_match(HP_CITIZEN)
    }
]

class HPCitizen(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.priority = PRIORITY
    
    def get_type(self):
        return 'STORAGE'
    
    def get_manufacturer(self):
        manufacturer = get_canonical_string(self.get(HP_HTTP_MG_MANUFACTURER))
        
        if manufacturer and manufacturer != "HP":
            return manufacturer
        return "Hewlett-Packard"
    
    def get_firmware(self):
        return get_canonical_string(self.get(HP_HTTP_MG_VERSION))
    
    def get_serial(self):
        return get_canonical_string(self.get(HP_HTTP_MG_SERIAL_NUMBER))
    
    def get_model(self):
        return get_canonical_string(self.get(HP_HTTP_MG_PRODUCT))
    
    def run(self):
        device = self.device
        if not device:
            return
        
        manufacturer = self.get_manufacturer()
        if not manufacturer:
            return
        
        model = self.get_model()
        if not model:
            return
        
        # Add hardware version firmware if present
        hw_version = get_canonical_string(self.get(HP_HTTP_MG_HW_VERSION))
        if not empty(hw_version):
            device.addFirmware({
                'NAME': f"{model} HW",
                'DESCRIPTION': f"{model} HW version",
                'TYPE': "hardware",
                'VERSION': hw_version,
                'MANUFACTURER': manufacturer
            })
        
        # Add ROM version firmware if present and not null
        rom_version = get_canonical_string(self.get(HP_HTTP_MG_ROM_VERSION))
        if not empty(rom_version) and not re.match(r'^null$', rom_version, re.IGNORECASE):
            device.addFirmware({
                'NAME': f"{model} Rom",
                'DESCRIPTION': f"{model} Rom version",
                'TYPE': "hardware",
                'VERSION': rom_version,
                'MANUFACTURER': manufacturer
            })

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    hp_citizen = HPCitizen()
    print("Priority:", hp_citizen.priority)
    print("Type:", hp_citizen.get_type())
    print("Manufacturer:", hp_citizen.get_manufacturer())
    print("Firmware:", hp_citizen.get_firmware())
    print("Serial:", hp_citizen.get_serial())
    print("Model:", hp_citizen.get_model())
    
    # Mock device for run
    hp_citizen.device = MockDevice()
    print("\nBefore run - Firmwares:", hp_citizen.device.firmwares)
    hp_citizen.run()
    print("After run - Firmwares:")
    for fw in hp_citizen.device.firmwares:
        print(f"  - {fw['NAME']}: {fw['VERSION']} (Type: {fw['TYPE']})")
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::HPCitizen - Inventory module for HP Storage

This module enhances HP storage devices support.
"""
