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

def get_canonical_mac_address(mac):
    # Mock function to normalize MAC address format
    # Ensures proper MAC address format (XX:XX:XX:XX:XX:XX)
    if not mac:
        return None
    # Remove any existing separators and convert to uppercase
    mac = mac.replace(':', '').replace('-', '').upper()
    # Insert colons every 2 characters
    if len(mac) == 12:
        return ':'.join(mac[i:i+2] for i in range(0, 12, 2))
    return mac

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked
    
    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        # For now, returns mock values to test functionality
        mock_values = {
            '.1.3.6.1.2.1.1.1.0': 'HWg-STE2 v4.2.5',  # hwgModel (sysDescr)
            '.1.3.6.1.4.1.21796.4.5.70.1.0': '00:0A:DA:01:23:45',  # hwgWldMac
            '.1.3.6.1.4.1.21796.4.1.70.1.0': '00:0A:DA:67:89:AB',  # hwgSteMac
            '.1.3.6.1.4.1.21796.4.9.70.1.0': '00:0A:DA:CD:EF:01',  # hwgSte2Mac
        }
        return mock_values.get(oid, None)

# Constants
# See Hwg-MIB
HWG = '.1.3.6.1.4.1.21796'
HWG_MODEL = '.1.3.6.1.2.1.1.1.0'
HWG_WLD_MAC = HWG + '.4.5.70.1.0'
HWG_STE_MAC = HWG + '.4.1.70.1.0'
HWG_STE2_MAC = HWG + '.4.9.70.1.0'

mib_support = [
    {
        'name': 'hwg',
        'sysobjectid': get_regexp_oid_match(HWG)
    }
]

class Hwg(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_type(self):
        return 'NETWORKING'
    
    def get_manufacturer(self):
        return 'HW group s.r.o'
    
    def get_serial(self):
        # Try to get MAC address from any of the three possible OIDs
        mac = self.get(HWG_WLD_MAC) or self.get(HWG_STE_MAC) or self.get(HWG_STE2_MAC)
        
        serial = get_canonical_mac_address(get_canonical_string(mac))
        if not serial:
            return None
        
        # Remove colons to use MAC as serial number
        serial = serial.replace(':', '')
        
        return serial
    
    def get_mac_address(self):
        # Try to get MAC address from any of the three possible OIDs
        mac = self.get(HWG_WLD_MAC) or self.get(HWG_STE_MAC) or self.get(HWG_STE2_MAC)
        
        return get_canonical_mac_address(get_canonical_string(mac))
    
    def get_model(self):
        return self.get(HWG_MODEL)

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    hwg = Hwg()
    print("Type:", hwg.get_type())
    print("Manufacturer:", hwg.get_manufacturer())
    print("Serial:", hwg.get_serial())
    print("MAC Address:", hwg.get_mac_address())
    print("Model:", hwg.get_model())
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Hwg - Inventory module for Hwg

This module enhances Hwg devices support.
"""
