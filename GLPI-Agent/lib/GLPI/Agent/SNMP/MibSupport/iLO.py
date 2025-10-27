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
    if not mac:
        return None
    # Remove any existing separators and convert to uppercase
    mac = mac.replace(':', '').replace('-', '').upper()
    # Insert colons every 2 characters
    if len(mac) == 12:
        return ':'.join(mac[i:i+2] for i in range(0, 12, 2))
    return mac

def get_canonical_constant(value):
    # Mock function to get canonical constant value
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return str(value).strip()

# Simple mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None  # To be set externally; for testing, can be mocked
    
    def get(self, oid):
        # Mock SNMP get; in real use, implement SNMP fetch
        mock_values = {
            '.1.3.6.1.4.1.232.9.2.2.2.0': '2.78',  # cpqSm2Cntrl firmware version
            '.1.3.6.1.4.1.232.9.2.2.1.0': '05/21/2021',  # cpqSm2Cntrl firmware date
            '.1.3.6.1.4.1.232.9.2.2.15.0': 'ILOMXQ12345',  # cpqSm2Cntrl serial
        }
        return mock_values.get(oid, None)
    
    def getSequence(self, oid):
        # Mock function to get SNMP sequence/walk results
        # Returns array of values from a table walk
        # Index corresponds to: [0]=index, [1]=desc, [3]=mac, [4]=ip, [6]=status, [7]=duplex, [8]=speed, [11]=mtu
        mock_sequence = [
            1,  # index
            'iLO Network Interface',  # description
            None,  # unused
            '00:17:A4:77:88:99',  # MAC address
            '192.168.1.100',  # IP address
            None,  # unused
            2,  # status (2=up)
            3,  # duplex (3=full)
            100,  # speed in Mbps
            None,  # unused
            None,  # unused
            1500  # MTU
        ]
        return mock_sequence

# Mock Device class with addPort method
class MockDevice:
    def __init__(self):
        self.ports = {}
    
    def addPort(self, port_number, port_info):
        self.ports[port_number] = port_info

# Constants
# Constants extracted from Compaq cpqsm2.mib, as said in mib:
# Implementation of the cpqSm2Cntrl group is mandatory for all agents
# supporting the Remote Insight/Integrated Lights-Out MIB.
# All Compaq iLO sysobjectid starts with .1.3.6.1.4.1.232.9.4
COMPAQ = '.1.3.6.1.4.1.232'
CPQ_SM2_CNTRL = COMPAQ + '.9.2.2'
CPQ_SM2_NIC = COMPAQ + '.9.2.5'

mib_support = [
    {
        'name': 'cpqsm2',
        'sysobjectid': re.compile(r'^\.1\.3\.6\.1\.4\.1\.232\.9\.4')
    }
]

class iLO(MibSupportTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sm2seq = None  # Cache for cpqSm2NicConfigEntry sequence
    
    def get_firmware(self):
        return self.get(CPQ_SM2_CNTRL + '.2.0')
    
    def get_firmware_date(self):
        return self.get(CPQ_SM2_CNTRL + '.1.0')
    
    def get_serial(self):
        return self.get(CPQ_SM2_CNTRL + '.15.0')
    
    def get_mac_address(self):
        cpq_sm2_nic_config_entry = self._cpq_sm2_nic_config_entry()
        if not isinstance(cpq_sm2_nic_config_entry, list) or not cpq_sm2_nic_config_entry:
            return None
        
        return cpq_sm2_nic_config_entry[3]
    
    def get_ip(self):
        cpq_sm2_nic_config_entry = self._cpq_sm2_nic_config_entry()
        if not isinstance(cpq_sm2_nic_config_entry, list) or not cpq_sm2_nic_config_entry:
            return None
        
        return cpq_sm2_nic_config_entry[4]
    
    # TODO: Report server GUID so it is possible to link iLO to related host
    # def _get_server_guid(self):
    #     return self.get(CPQ_SM2_CNTRL + '.26.0')
    
    # Handle cached cpqSm2NicConfigEntry sequence to limit walk during netinventory
    def _cpq_sm2_nic_config_entry(self):
        if self._sm2seq is not None:
            return self._sm2seq
        
        self._sm2seq = self.getSequence(CPQ_SM2_NIC + '.1.1')
        return self._sm2seq
    
    def run(self):
        device = self.device
        if not device:
            return
        
        cpq_sm2_nic_config_entry = self._cpq_sm2_nic_config_entry()
        if not isinstance(cpq_sm2_nic_config_entry, list) or not cpq_sm2_nic_config_entry:
            return
        
        # Status mapping: index corresponds to status value, maps to IFSTATUS
        status = ['-', '2', '1', '2']
        
        status_value = get_canonical_constant(cpq_sm2_nic_config_entry[6])
        if status_value is not None and 0 <= status_value < len(status):
            ifstatus = status[status_value]
        else:
            ifstatus = '2'
        
        port = {
            'IFNUMBER': 1,
            'IFDESCR': get_canonical_string(cpq_sm2_nic_config_entry[1]),
            'MAC': get_canonical_mac_address(cpq_sm2_nic_config_entry[3]),
            'IFSTATUS': ifstatus,
            'IFPORTDUPLEX': get_canonical_constant(cpq_sm2_nic_config_entry[7]),
            'IFSPEED': get_canonical_constant(cpq_sm2_nic_config_entry[8]) * 1000,
            'IFMTU': get_canonical_constant(cpq_sm2_nic_config_entry[11]),
            'IPS': {
                'IP': [cpq_sm2_nic_config_entry[4]]
            }
        }
        
        device.addPort(1, port)

# For testing/standalone run
if __name__ == "__main__":
    # Test instantiation
    ilo = iLO()
    print("Firmware:", ilo.get_firmware())
    print("Firmware Date:", ilo.get_firmware_date())
    print("Serial:", ilo.get_serial())
    print("MAC Address:", ilo.get_mac_address())
    print("IP Address:", ilo.get_ip())
    
    # Mock device for run
    ilo.device = MockDevice()
    print("\nBefore run - Ports:", ilo.device.ports)
    ilo.run()
    print("After run - Ports:")
    for port_num, port_info in ilo.device.ports.items():
        print(f"  Port {port_num}:")
        for key, value in port_info.items():
            print(f"    {key}: {value}")
    
    print("\nModule loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::iLO - Inventory module for HP iLO (Integrated Lights-Out)

This module enhances HP iLO support for Remote Insight/Integrated Lights-Out devices.
"""
