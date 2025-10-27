import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_regexp_oid_match(oid):
    # Returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

def get_canonical_string(value):
    # Mock function to get canonical string representation
    if value is None:
        return None
    return str(value).strip()

def get_canonical_constant(value):
    # Mock function to get canonical constant value
    if value is None:
        return None
    # In real implementation, this would handle constant normalization
    return str(value).strip()

def hex2char(value):
    # Mock function to convert hex-encoded string to characters
    if value is None:
        return None
    # In real implementation, this would handle hex to char conversion
    # For now, just return the string as-is
    return str(value)

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked
        self.priority = 1  # Default priority
    
    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        mock_values = {
            '.1.3.6.1.4.1.11.2.3.9.1.1.7.0': 'MODEL: HP LaserJet Pro M404dn; SN: ABCD123456; FW: 002.2208A',
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.2.0': 'HP LaserJet Pro M404dn',  # model_name
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.3.0': 'ABCD123456',  # serial_number
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.5.0': '20220815',  # fw_rom_datecode
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.6.0': '002.2208A',  # fw_rom
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.5.0': '12345',  # totalEnginePageCount
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.7.0': '5432',   # totalColorPageCount
            '.1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.22.0': '2345',  # duplexPageCount
        }
        return mock_values.get(oid, None)

# Mock Device class
class MockDevice:
    def __init__(self):
        self.MANUFACTURER = None
        self.DESCRIPTION = None
        self.PAGECOUNTERS = {}

# Constants
PRIORITY = 9

# See HP-LASERJET-COMMON-MIB / JETDIRECT3-MIB
HP_PERIPHERAL = '.1.3.6.1.4.1.11.2.3.9'  # hp.nm.system.net-peripheral
HP_OFFICE_PRINTER = '.1.3.6.1.4.1.29999'
HP_SYSTEM = '.1.3.6.1.4.1.11.1'
HP_NET_PRINTER = HP_PERIPHERAL + '.1'
HP_DEVICE = HP_PERIPHERAL + '.4.2.1'  # + netPML.netPMLmgmt.device

GD_STATUS_ID = HP_NET_PRINTER + '.1.7.0'

# System id
SYSTEM_ID = HP_DEVICE + '.1.3'  # + system.id
MODEL_NAME = SYSTEM_ID + '.2.0'
SERIAL_NUMBER = SYSTEM_ID + '.3.0'
FW_ROM_DATECODE = SYSTEM_ID + '.5.0'
FW_ROM = SYSTEM_ID + '.6.0'

# Status print engine: status-prt-eng
STATUS_PRT_ENGINE = HP_DEVICE + '.4.1.2'
TOTAL_ENGINE_PAGE_COUNT = STATUS_PRT_ENGINE + '.5.0'
TOTAL_COLOR_PAGE_COUNT = STATUS_PRT_ENGINE + '.7.0'
DUPLEX_PAGE_COUNT = STATUS_PRT_ENGINE + '.22.0'

# HP LaserJet Pro MFP / Marvel ASIC
HP_LASERJET_PRO_MFP = '.1.3.6.1.4.1.26696.1'

counters = {
    'TOTAL': TOTAL_ENGINE_PAGE_COUNT,
    'COLOR': TOTAL_COLOR_PAGE_COUNT,
    'DUPLEX': DUPLEX_PAGE_COUNT
}

mib_support = [
    {
        'name': 'hp-peripheral',
        'sysobjectid': get_regexp_oid_match(HP_PERIPHERAL)
    },
    {
        'name': 'hp-office',
        'sysobjectid': get_regexp_oid_match(HP_OFFICE_PRINTER)
    },
    {
        'name': 'hp-system',
        'sysobjectid': get_regexp_oid_match(HP_SYSTEM)
    },
    {
        'name': 'hp-laserjet-pro-mfp',
        'sysobjectid': get_regexp_oid_match(HP_LASERJET_PRO_MFP)
    },
    {
        'name': 'hp-peripheral-oid',
        'privateoid': GD_STATUS_ID
    }
]

class HPNetPeripheral(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.priority = PRIORITY
    
    def get_type(self):
        return 'PRINTER'
    
    def get_manufacturer(self):
        device = self.device
        if not device:
            return None
        
        if device.MANUFACTURER:
            return None
        
        return "Hewlett-Packard"
    
    def get_firmware(self):
        device = self.device
        if not device:
            return None
        
        firmware = self._get_clean(FW_ROM)
        
        # Eventually extract EEPROM revision from device description
        if not firmware and device.DESCRIPTION:
            for part in device.DESCRIPTION.split(','):
                match = re.search(r'EEPROM\s+(\S+)', part)
                if match:
                    return match.group(1)
        
        # Then try to get firmware if set in StatusId string
        status_id = get_canonical_string(self.get(GD_STATUS_ID))
        if status_id:
            for part in status_id.split(';'):
                part = part.strip()
                match = re.match(r'^FW:\s*(.*)$', part)
                if match:
                    firmware = match.group(1)
                    break
        
        return firmware
    
    def get_firmware_date(self):
        return self._get_clean(FW_ROM_DATECODE)
    
    def get_serial(self):
        sn = self.get(SERIAL_NUMBER)
        if sn:
            return sn
        
        # Then try to get serial if set in StatusId string
        status_id = get_canonical_string(self.get(GD_STATUS_ID))
        if status_id:
            for part in status_id.split(';'):
                part = part.strip()
                match = re.match(r'^SN:\s*(.*)$', part)
                if match:
                    sn = match.group(1)
                    break
        
        return sn
    
    def get_model(self):
        # Try first to get model if set in StatusId string
        status_id = get_canonical_string(self.get(GD_STATUS_ID))
        if status_id:
            for part in status_id.split(';'):
                part = part.strip()
                match = re.match(r'^MODEL:\s*(.*)$', part)
                if match:
                    return match.group(1)
        
        # Else try to get model from model-name string
        return self._get_clean(MODEL_NAME)
    
    def run(self):
        device = self.device
        if not device:
            return
        
        # Update counters if still not found
        for counter_name, counter_oid in counters.items():
            # Skip if counter already exists
            if device.PAGECOUNTERS and device.PAGECOUNTERS.get(counter_name):
                continue
            
            count = self.get(counter_oid)
            if not count:
                continue
            
            device.PAGECOUNTERS[counter_name] = get_canonical_constant(count)
    
    def _get_clean(self, oid):
        clean_string = hex2char(self.get(oid))
        
        if clean_string is None:
            return None
        
        # Remove non-printable characters
        clean_string = re.sub(r'[^\x20-\x7E]', '', clean_string)
        
        return clean_string

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    hp_net_peripheral = HPNetPeripheral()
    print("Priority:", hp_net_peripheral.priority)
    print("Type:", hp_net_peripheral.get_type())
    
    # Mock device for testing
    hp_net_peripheral.device = MockDevice()
    hp_net_peripheral.device.DESCRIPTION = "HP LaserJet, EEPROM V.35.21"
    
    print("Manufacturer:", hp_net_peripheral.get_manufacturer())
    print("Firmware:", hp_net_peripheral.get_firmware())
    print("Firmware Date:", hp_net_peripheral.get_firmware_date())
    print("Serial:", hp_net_peripheral.get_serial())
    print("Model:", hp_net_peripheral.get_model())
    
    # Test run method
    print("\nBefore run - Page Counters:", hp_net_peripheral.device.PAGECOUNTERS)
    hp_net_peripheral.run()
    print("After run - Page Counters:", hp_net_peripheral.device.PAGECOUNTERS)
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::HPNetPeripheral - Inventory module for HP Printers

This module enhances HP printers devices support.
"""
