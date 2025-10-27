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
            '.1.3.6.1.4.1.39165.1.1.0': 'DS-2CD2385G1-I',  # hikvisionModel
            '.1.3.6.1.4.1.39165.1.4.0': '00-11-22-AA-BB-CC',  # hikvisionMac
        }
        return mock_values.get(oid, None)

# Constants
HIKVISION = '.1.3.6.1.4.1.39165'
HIKVISION_MODEL = HIKVISION + '.1.1.0'
HIKVISION_MAC = HIKVISION + '.1.4.0'

mib_support = [
    {
        'name': 'hikvision',
        'sysobjectid': get_regexp_oid_match(HIKVISION)
    },
    {
        'name': 'hikvision-model',
        'privateoid': HIKVISION_MODEL
    }
]

class Hikvision(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_type(self):
        return 'NETWORKING'
    
    def get_manufacturer(self):
        return 'Hikvision'
    
    def get_serial(self):
        serial = get_canonical_string(self.get(HIKVISION_MAC))
        if not serial:
            return None
        # Remove dashes from MAC address to use as serial
        serial = serial.replace('-', '')
        return serial
    
    def get_mac_address(self):
        mac = get_canonical_string(self.get(HIKVISION_MAC))
        if not mac:
            return None
        # Replace dashes with colons
        mac = mac.replace('-', ':')
        return get_canonical_mac_address(mac)
    
    def get_snmp_hostname(self):
        serial = self.get_serial()
        if not serial:
            return None
        
        device = self.device
        if not device:
            return None
        
        model = device.get('MODEL')
        if model:
            return f"{model}_{serial}"
        return None
    
    def get_model(self):
        return self.get(HIKVISION_MODEL)

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    hikvision = Hikvision()
    print("Type:", hikvision.get_type())
    print("Manufacturer:", hikvision.get_manufacturer())
    print("Serial:", hikvision.get_serial())
    print("MAC Address:", hikvision.get_mac_address())
    print("Model:", hikvision.get_model())
    
    # Mock device for getSnmpHostname
    hikvision.device = {'MODEL': 'DS-2CD2385G1-I'}
    print("SNMP Hostname:", hikvision.get_snmp_hostname())
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::Hikvision - Inventory module for Hikvision

This module enhances Hikvision devices support.
"""
