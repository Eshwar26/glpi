import re

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

def empty(value):
    return value is None or str(value).strip() == ''

def is_integer(value):
    if value is None:
        return False
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

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
            '.1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.1.0': 'SN123456789',  # brInfoSerialNumber
            '.1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.54.2.2.1.3.3': '123',  # brScanCountCounter
            '.1.3.6.1.4.1.2435.2.4.3.1240.1.1.0': 'NodeName',  # brpsNodeName
            '.1.3.6.1.4.1.2435.2.4.3.1240.1.3.0': 'HardwareType',  # brpsHardwareType
            '.1.3.6.1.4.1.2435.2.4.3.1240.1.4.0': '1.2.3',  # brpsMainRevision
            '.1.3.6.1.4.1.2435.2.4.3.1240.1.12.0': 'Brother MFC-L2710DW',  # brpsServerDescription
        }
        return mock_values.get(oid, None)

    def walk(self, oid):
        # Mock SNMP walk; returns dict of index: value
        mock_walks = {
            '.1.3.6.1.4.1.2435.2.4.4.1240.1.5.1.2': {'1': '1', '2': '2'},  # brMultiIFType
            '.1.3.6.1.4.1.2435.2.4.4.1240.1.5.1.8': {'1': 'eth0', '2': 'wlan0'},  # brMultiIFNodeType
        }
        return mock_walks.get(oid, {})

# Constants
PRIORITY = 5

BROTHER = '.1.3.6.1.4.1.2435'

NET_PERIPHERAL = BROTHER + '.2.3.9'

PRINTERINFORMATION = NET_PERIPHERAL + '.4.2.1.5.5'

BR_INFO_SERIAL_NUMBER = PRINTERINFORMATION + '.1.0'

BR_SCAN_COUNT_COUNTER = PRINTERINFORMATION + '.54.2.2.1.3.3'

BR_MULTI_IF_CONFIGURE_ENTRY = BROTHER + '.2.4.4.1240.1.5.1'

BR_MULTI_IF_TYPE = BR_MULTI_IF_CONFIGURE_ENTRY + '.2'

BR_MULTI_IF_NODE_TYPE = BR_MULTI_IF_CONFIGURE_ENTRY + '.8'

BRNETCONFIG = BROTHER + '.2.4.3.1240'

BRCONFIG = BRNETCONFIG + '.1'

BRPS_NODE_NAME = BRCONFIG + '.1.0'

BRPS_HARDWARE_TYPE = BRCONFIG + '.3.0'

BRPS_MAIN_REVISION = BRCONFIG + '.4.0'

BRPS_SERVER_DESCRIPTION = BRCONFIG + '.12.0'

mib_support = [
    {
        'name': 'brother-netconfig',
        'privateoid': BRPS_HARDWARE_TYPE
    }
]

class BrotherNetConfig(MibSupportTemplate):
    def get_firmware(self):
        return get_canonical_string(self.get(BRPS_MAIN_REVISION))

    def get_snmp_hostname(self):
        return get_canonical_string(self.get(BRPS_NODE_NAME))

    def get_serial(self):
        return get_canonical_string(self.get(BR_INFO_SERIAL_NUMBER))

    def get_manufacturer(self):
        description = get_canonical_string(self.get(BRPS_SERVER_DESCRIPTION))
        if not empty(description) and re.match(r'^Brother .*', description, re.IGNORECASE):
            return 'Brother'
        return None

    def get_model(self):
        device = self.device
        if device and device.get('MODEL'):
            device['MODEL'] = re.sub(r'^Brother\s+', '', device['MODEL'])
            return device['MODEL']

        description = get_canonical_string(self.get(BRPS_SERVER_DESCRIPTION))
        match = re.match(r'^Brother (.*)', description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def update_port_if_type(self):
        device = self.device
        if not device:
            return

        # Get list of device ports
        ports = device.get('PORTS', {}).get('PORT', {})

        # Get list of device ports types (lan(1)/wirelesslan(2))
        br_multi_if_type = self.walk(BR_MULTI_IF_TYPE)
        if not br_multi_if_type:
            return

        # Get list of device ports names
        br_multi_if_node_type = self.walk(BR_MULTI_IF_NODE_TYPE)
        if not br_multi_if_node_type:
            return

        for index in br_multi_if_type:
            for port in ports:
                if ports[port].get('IFNAME') and br_multi_if_node_type.get(index):
                    if ports[port]['IFNAME'] == get_canonical_string(br_multi_if_node_type[index]):
                        # wirelesslan(2)
                        if_type_val = br_multi_if_type[index]
                        if is_integer(if_type_val) and int(if_type_val) == 2:
                            # ieee80211(71)
                            ports[port]['IFTYPE'] = 71

    def run(self):
        device = self.device
        if not device:
            return

        mapping = {
            'SCANNED': BR_SCAN_COUNT_COUNTER,
        }

        for counter in sorted(mapping):
            count = self.get(mapping[counter])
            if count:
                if 'PAGECOUNTERS' not in device:
                    device['PAGECOUNTERS'] = {}
                device['PAGECOUNTERS'][counter] = count

        self.update_port_if_type()

# For testing/standalone run (optional)
if __name__ == "__main__":
    # Mock Device dict for testing
    device = {
        'MODEL': 'Brother MFC-L2710DW',
        'PORTS': {
            'PORT': {
                '1': {'IFNAME': 'eth0'},
                '2': {'IFNAME': 'wlan0'}
            }
        }
    }

    # Test instantiation
    brother = BrotherNetConfig()
    brother.device = device
    print("Firmware:", brother.get_firmware())
    print("SNMP Hostname:", brother.get_snmp_hostname())
    print("Serial:", brother.get_serial())
    print("Manufacturer:", brother.get_manufacturer())
    print("Model:", brother.get_model())
    print("Before run - PAGECOUNTERS:", device.get('PAGECOUNTERS', 'None'))
    print("Before run - Ports:", device['PORTS']['PORT'])
    brother.run()
    print("After run - PAGECOUNTERS:", device.get('PAGECOUNTERS', 'None'))
    print("After run - Ports:", device['PORTS']['PORT'])
    print("Module loaded and run successfully without errors.")
