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

def get_canonical_size(size_str):
    # Mock function to convert size string to canonical format
    # e.g., "1000000000 bytes" -> "1 GB"
    if not size_str:
        return None
    match = re.match(r'(\d+)\s*bytes', str(size_str))
    if match:
        bytes_val = int(match.group(1))
        if bytes_val >= 1024**4:
            return f"{bytes_val / (1024**4):.2f} TB"
        elif bytes_val >= 1024**3:
            return f"{bytes_val / (1024**3):.2f} GB"
        elif bytes_val >= 1024**2:
            return f"{bytes_val / (1024**2):.2f} MB"
        else:
            return f"{bytes_val} bytes"
    return size_str

def get_canonical_manufacturer(manufacturer):
    # Mock function to normalize manufacturer name
    if not manufacturer:
        return None
    # Add manufacturer normalization logic here
    return manufacturer.strip().upper()

def get_canonical_serial_number(serial):
    # Mock function to normalize serial number
    if serial is None:
        return None
    return str(serial).strip()

def trim_whitespace(value):
    # Remove leading and trailing whitespace
    if value is None:
        return None
    return str(value).strip()

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked
    
    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        mock_values = {
            '.1.3.6.1.4.1.1714.1.1.1.1.4.0': '3',  # fwMajorVersion
            '.1.3.6.1.4.1.1714.1.1.1.1.5.0': '52',  # fwMinorVersion
            '.1.3.6.1.4.1.1714.1.1.1.1.10.0': 'S12345678',  # serialNum
            '.1.3.6.1.4.1.1714.1.1.1.1.15.0': 'EonStor DS 3024',  # privateLogoModel
        }
        return mock_values.get(oid, None)
    
    def walk(self, oid):
        # Mock SNMP walk; returns dictionary of OID -> value
        # Simulating multiple hard drives in the storage array
        if oid == '.1.3.6.1.4.1.1714.1.1.6.1.11':  # hddStatus
            return {
                '.1.3.6.1.4.1.1714.1.1.6.1.11.1': 0x10,  # healthy disk
                '.1.3.6.1.4.1.1714.1.1.6.1.11.2': 0x10,  # healthy disk
                '.1.3.6.1.4.1.1714.1.1.6.1.11.3': 0xff,  # missing disk (skip)
            }
        elif oid == '.1.3.6.1.4.1.1714.1.1.6.1.7':  # hddSize (block count)
            return {
                '.1.3.6.1.4.1.1714.1.1.6.1.7.1': 1953525168,
                '.1.3.6.1.4.1.1714.1.1.6.1.7.2': 1953525168,
            }
        elif oid == '.1.3.6.1.4.1.1714.1.1.6.1.8':  # hddBlkSizeIdx (power of 2)
            return {
                '.1.3.6.1.4.1.1714.1.1.6.1.8.1': 9,  # 2^9 = 512 bytes
                '.1.3.6.1.4.1.1714.1.1.6.1.8.2': 9,
            }
        elif oid == '.1.3.6.1.4.1.1714.1.1.6.1.15':  # hddModelStr
            return {
                '.1.3.6.1.4.1.1714.1.1.6.1.15.1': 'SEAGATE ST1000NM0033',
                '.1.3.6.1.4.1.1714.1.1.6.1.15.2': 'WDC WD1003FBYX',
            }
        elif oid == '.1.3.6.1.4.1.1714.1.1.6.1.16':  # hddFwRevStr
            return {
                '.1.3.6.1.4.1.1714.1.1.6.1.16.1': 'SN03',
                '.1.3.6.1.4.1.1714.1.1.6.1.16.2': '01.01D02',
            }
        elif oid == '.1.3.6.1.4.1.1714.1.1.6.1.17':  # hddSerialNum
            return {
                '.1.3.6.1.4.1.1714.1.1.6.1.17.1': 'Z1W0ABCD',
                '.1.3.6.1.4.1.1714.1.1.6.1.17.2': 'WD-WXYZ1234',
            }
        return {}

# Mock Device class
class MockDevice:
    def __init__(self):
        self.STORAGES = []

# Constants
# See IFT-SNMP-MIB
INFORTREND = '.1.3.6.1.4.1.1714'

EXT_INTERFACE = INFORTREND + '.1.1'
CTLR_CONFIGURATION = EXT_INTERFACE + '.1'

SYS_INFORMATION = CTLR_CONFIGURATION + '.1'
FW_MAJOR_VERSION = SYS_INFORMATION + '.4.0'
FW_MINOR_VERSION = SYS_INFORMATION + '.5.0'
SERIAL_NUM = SYS_INFORMATION + '.10.0'
PRIVATE_LOGO_MODEL = SYS_INFORMATION + '.15.0'

HDD_TABLE = EXT_INTERFACE + '.6'
HDD_SIZE = HDD_TABLE + '.1.7'
HDD_BLK_SIZE_IDX = HDD_TABLE + '.1.8'
HDD_STATUS = HDD_TABLE + '.1.11'
HDD_MODEL_STR = HDD_TABLE + '.1.15'
HDD_FW_REV_STR = HDD_TABLE + '.1.16'
HDD_SERIAL_NUM = HDD_TABLE + '.1.17'

mib_support = [
    {
        'name': 'infortrend',
        'sysobjectid': get_regexp_oid_match(EXT_INTERFACE)
    }
]

class Infortrend(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_serial(self):
        return self.get(SERIAL_NUM)
    
    def get_model(self):
        return self.get(PRIVATE_LOGO_MODEL)
    
    def get_firmware(self):
        major = self.get(FW_MAJOR_VERSION)
        minor = self.get(FW_MINOR_VERSION)
        if major and minor:
            return f"{major}.{minor}"
        return None
    
    def get_type(self):
        return 'STORAGE'
    
    def get_manufacturer(self):
        return "Infortrend Technology, Inc."
    
    def run(self):
        device = self.device
        if not device:
            return
        
        # Scan storages
        hdd_status = self.walk(HDD_STATUS)
        if not hdd_status:
            return
        
        if not isinstance(hdd_status, dict):
            return
        
        hdd_size = self.walk(HDD_SIZE)
        hdd_blk_size_idx = self.walk(HDD_BLK_SIZE_IDX)
        
        hdd_model_str = self.walk(HDD_MODEL_STR)
        hdd_fw_rev_str = self.walk(HDD_FW_REV_STR)
        hdd_serial_num = self.walk(HDD_SERIAL_NUM)
        
        for key in sorted(hdd_status.keys()):
            status = hdd_status.get(key)
            if status is None:
                continue
            
            # Do not inventory missing disks
            if status in [0x3f, 0xfc, 0xfd, 0xfe, 0xff]:
                continue
            
            storage = {
                'TYPE': 'disk',
            }
            
            # Handle size
            if hdd_size.get(key) is not None and hdd_blk_size_idx.get(key) is not None:
                blockcount = hdd_size[key]
                # Fix signed values as 32 bits encoded values
                if blockcount < 0:
                    blockcount = (1 << 32) + blockcount + 1
                blocksize = 1 << hdd_blk_size_idx[key]
                bytes_val = blocksize * blockcount
                storage['DISKSIZE'] = get_canonical_size(f"{bytes_val} bytes")
            
            # Handle model and manufacturer
            if hdd_model_str.get(key):
                string = trim_whitespace(get_canonical_string(hdd_model_str[key]))
                storage['NAME'] = string
                # Extract manufacturer and model from string like "SEAGATE ST1000NM0033"
                match = re.match(r'(\S+)[ _]+(.*)\s*$', string)
                if match:
                    manufacturer = match.group(1)
                    model = match.group(2)
                    if model:
                        storage['MODEL'] = model
                    if manufacturer:
                        storage['MANUFACTURER'] = get_canonical_manufacturer(manufacturer)
            
            # Handle firmware
            if hdd_fw_rev_str.get(key):
                storage['FIRMWARE'] = get_canonical_string(hdd_fw_rev_str[key])
            
            # Handle serial
            if hdd_serial_num.get(key):
                storage['SERIAL'] = get_canonical_serial_number(hdd_serial_num[key])
            
            # Only keep storage if we got model and serial
            if storage.get('MODEL') and storage.get('SERIAL'):
                device.STORAGES.append(storage)

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    infortrend = Infortrend()
    print("Type:", infortrend.get_type())
    print("Manufacturer:", infortrend.get_manufacturer())
    print("Serial:", infortrend.get_serial())
    print("Model:", infortrend.get_model())
    print("Firmware:", infortrend.get_firmware())
    
    # Mock device for run
    infortrend.device = MockDevice()
    print("\nBefore run - Storages:", infortrend.device.STORAGES)
    infortrend.run()
    print("After run - Storages found:", len(infortrend.device.STORAGES))
    for i, storage in enumerate(infortrend.device.STORAGES, 1):
        print(f"\n  Storage {i}:")
        for key, value in storage.items():
            print(f"    {key}: {value}")
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Infortrend - Inventory module for Infortrend SAN

This module enhances Infortrend SAN support.
"""
