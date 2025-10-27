import re

# Mock or simple implementations for GLPI Agent functions/tools
def hex2char(hexstr):
    if not hexstr:
        return None
    try:
        return bytes.fromhex(hexstr).decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return None

def get_regexp_oid_match(oid):
    # Assuming it returns a compiled regex for exact prefix match
    return re.compile(f'^{re.escape(oid)}')

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked

    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns None or mock for specific OIDs
        return None

    def walk(self, oid):
        # Mock SNMP walk; returns dict of index: value
        mock_walks = {
            '.1.3.6.1.4.1.1248.1.2.2.2.1.1.2': {  # fw_base + '.2' versions
                '1': '312e302e30',  # hex for '1.0.0'
            },
            '.1.3.6.1.4.1.1248.1.2.2.2.1.1.3': {  # fw_base + '.3' names
                '1': '486561646572',  # hex for 'Header'
            },
            '.1.3.6.1.4.1.1248.1.2.2.2.1.1.4': {  # fw_base + '.4' firmwares
                '1': '486561646572',  # hex for 'Header'
            },
            '.1.3.6.1.4.1.1248.1.2.2.28.1.1.5': {  # cartridge_label
                '1': '4d61696e74656e616e6365',  # hex for 'Maintenance'
            },
            '.1.3.6.1.4.1.1248.1.2.2.28.1.1.2': {  # cartridge_level
                '1': '75',  # 75%
            },
        }
        return mock_walks.get(oid, {})

# Mock Device class for compatibility
class MockDevice:
    def __init__(self):
        self.firmwares = []
        self.cartridges = {}

    def add_firmware(self, firmware):
        self.firmwares.append(firmware)
        print(f"Added firmware: {firmware}")

# Constants
EPSON = '.1.3.6.1.4.1.1248'

MODEL = EPSON + '.1.2.2.1.1.1.2.1'
SERIAL = EPSON + '.1.2.2.1.1.1.5.1'
FW_BASE = EPSON + '.1.2.2.2.1.1'

CARTRIDGE_LEVEL = EPSON + '.1.2.2.28.1.1.2'
CARTRIDGE_LABEL = EPSON + '.1.2.2.28.1.1.5'

mib_support = [
    {
        'name': 'epson-printer',
        'sysobjectid': get_regexp_oid_match(EPSON)
    }
]

class Epson(MibSupportTemplate):
    def get_serial(self):
        return self.get(SERIAL)

    def get_model(self):
        return self.get(MODEL)

    def run(self):
        device = self.device
        if not device:
            return

        versions = self.walk(FW_BASE + '.2') or {}
        names = self.walk(FW_BASE + '.3') or {}
        firmwares = self.walk(FW_BASE + '.4') or names
        if firmwares:
            for index in firmwares:
                if index in versions:
                    name_decoded = hex2char(names.get(index, ''))
                    version_decoded = hex2char(versions[index])
                    firmware = {
                        'NAME': f"Epson {name_decoded or 'printer'}",
                        'DESCRIPTION': f"Epson printer {name_decoded or 'firmware'} firmware",
                        'TYPE': 'printer',
                        'VERSION': version_decoded,
                        'MANUFACTURER': 'Epson'
                    }
                    device.add_firmware(firmware)

        # Search for any maintenance cartridge level
        cartridges = self.walk(CARTRIDGE_LABEL)
        if cartridges:
            levels = self.walk(CARTRIDGE_LEVEL)
            for key in sorted(cartridges):
                label = hex2char(cartridges[key])
                if label and 'maintenance' in label.lower():
                    if key in levels:
                        if 'CARTRIDGES' not in device:
                            device['CARTRIDGES'] = {}
                        device['CARTRIDGES']['MAINTENANCEKIT'] = levels[key]
                        break

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device for testing
    mock_device = MockDevice()

    # Test instantiation
    epson = Epson()
    epson.device = mock_device
    print("Serial:", epson.get_serial())
    print("Model:", epson.get_model())
    print("Before run - Firmwares:", len(mock_device.firmwares))
    print("Before run - Cartridges:", mock_device.cartridges)
    epson.run()
    print("After run - Firmwares:", len(mock_device.firmwares))
    print("After run - Cartridges:", mock_device.cartridges)
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Epson - Inventory module for Epson Printers

The module enhances Epson printers devices support.
"""
