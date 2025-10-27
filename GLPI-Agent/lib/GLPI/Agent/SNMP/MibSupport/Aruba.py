import re
from typing import Dict, List, Any, Optional

# Utility functions
def empty(val: Any) -> bool:
    """Check if a value is None or an empty string after trimming."""
    return val is None or str(val).strip() == ''

def getCanonicalString(value: Optional[str]) -> Optional[str]:
    """Mock implementation of getCanonicalString: Returns trimmed string or None."""
    if value is None or not str(value).strip():
        return None
    return str(value).strip()

def getCanonicalMacAddress(value: Optional[str]) -> Optional[str]:
    """Mock implementation of getCanonicalMacAddress: Formats MAC address."""
    if not value:
        return None
    # Assuming value is a hex string like '001122334455'
    if len(value) != 12:
        return None
    try:
        mac = ':'.join(value[i:i+2] for i in range(0, 12, 2)).upper()
        return mac
    except Exception:
        return None

def getRegexpOidMatch(oid: str) -> str:
    """Mock implementation of getRegexpOidMatch: Returns a regex pattern for the OID."""
    escaped_oid = re.escape(oid)
    return rf'^{escaped_oid}\..*'

# See Q-BRIDGE-MIB
DOT1Q_TP_FDB_STATUS = '.1.3.6.1.2.1.17.7.1.2.2.1.3'

# See ARUBA-MIB
ARUBA = '.1.3.6.1.4.1.14823'

# See AI-AP-MIB
AI_MIB = ARUBA + '.2.3.3.1'

AI_VIRTUAL_CONTROLLER_VERSION = AI_MIB + '.1.4.0'
AI_AP_SERIAL_NUM = AI_MIB + '.2.1.1.4'
AI_AP_MODEL_NAME = AI_MIB + '.2.1.1.6'
AI_WLAN_ESSID = AI_MIB + '.2.3.1.3'
AI_WLAN_MAC_ADDRESS = AI_MIB + '.2.3.1.4'

MIB_SUPPORT = [
    {
        'name': "aruba",
        'sysobjectid': getRegexpOidMatch(ARUBA)
    }
]

# Mock Device class to simulate device interactions
class Device:
    def __init__(self):
        self.DESCRIPTION = "ArubaOS (MODEL: AP-325)"
        self.PORTS = {
            'PORT': {
                '1': {'MAC': '00:1A:1E:00:01:01', 'IFDESCR': 'radio0_ssid_id0'},
                '2': {'MAC': '00:1A:1E:00:01:02', 'IFDESCR': 'radio1_ssid_id1'}
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default) if hasattr(self, key) else self.__dict__.get(key, default)

# Mock base class to simulate GLPIAgentSNMPMibSupportTemplate
class GLPIAgentSNMPMibSupportTemplate:
    def __init__(self, device: Optional[Device] = None):
        self.device = device
        self._snmp_data = {}  # Simulated SNMP data store

    def get(self, oid: str) -> Optional[str]:
        """Mock SNMP get operation."""
        mock_data = {
            AI_VIRTUAL_CONTROLLER_VERSION: "8.7.1.0",
            AI_AP_SERIAL_NUM + '.1': "AR123456789",
            AI_AP_MODEL_NAME + '.1': "325",
        }
        return mock_data.get(oid)

    def walk(self, oid: str) -> Optional[Dict[str, str]]:
        """Mock SNMP walk operation."""
        mock_data = {
            DOT1Q_TP_FDB_STATUS: {'1.1': '4', '1.2': '3'},
            AI_WLAN_ESSID: {'0': 'CorpWiFi', '1': 'GuestWiFi'},
            AI_WLAN_MAC_ADDRESS: {'0': '001A1E000101', '1': '001A1E000102'}
        }
        return mock_data.get(oid, {})

class GLPIAgentSNMPMibSupportAruba(GLPIAgentSNMPMibSupportTemplate):
    """
    Inventory module for Aruba AP

    The module enhances Aruba wifi access point devices support.
    """

    def get_firmware(self):
        return getCanonicalString(self.get(AI_VIRTUAL_CONTROLLER_VERSION))

    def _this(self):
        if not hasattr(self, '_this') or self._this is None:
            # Find reference to our device
            dot1q_tp_fdb_status = self.walk(DOT1Q_TP_FDB_STATUS)
            if dot1q_tp_fdb_status:
                for subkey, status in dot1q_tp_fdb_status.items():
                    if status == '4':
                        extracted_match = re.match(r'^\d+\.(.*)$', subkey)
                        if extracted_match:
                            extracted = extracted_match.group(1)
                            if not empty(extracted):
                                self._this = extracted
                                break
        return getattr(self, '_this', None)

    def get_serial(self):
        this = self._this()
        if not this:
            return None
        return getCanonicalString(self.get(AI_AP_SERIAL_NUM + '.' + this))

    def get_model(self):
        this = self._this()
        if this:
            model = getCanonicalString(self.get(AI_AP_MODEL_NAME + '.' + this))
            if model:
                return "AP " + model

        device = self.device
        if not device:
            return None

        model = None
        description = device.get('DESCRIPTION')
        if description:
            description_match = re.match(r'^ArubaOS\s+\(MODEL:\s*(.*)\)', description)
            if description_match:
                model = description_match.group(1)

        if not model:
            return None

        # Adjust to avoid duplication: if model starts with 'AP-', return as is; else prefix 'AP '
        if model.startswith('AP-'):
            return model
        else:
            return "AP " + model

    def run(self):
        device = self.device
        if not device:
            return

        # Get list of device ports (e.g. radioX_ssid_idY)
        ports = device.get('PORTS', {}).get('PORT', {})

        # Equivalent to "show ap bss-table" Aruba IAP CLI output command:
        # Get list of SSID
        ai_wlan_essid_values = self.walk(AI_WLAN_ESSID) or {}
        # Get list of Radios (e.g. radioX_ssid_idY etc.)
        ai_wlan_mac_address_values = self.walk(AI_WLAN_MAC_ADDRESS) or {}

        for index in ai_wlan_mac_address_values:
            # Get WLAN BSSID (e.g. XX:XX:XX:XX:XX:XX)
            wlan_mac_address = getCanonicalMacAddress(ai_wlan_mac_address_values[index])
            if not wlan_mac_address:
                continue

            for port in ports:
                if_mac_address = ports[port].get('MAC')
                if not if_mac_address or if_mac_address != wlan_mac_address:
                    continue

                if_descr = ports[port].get('IFDESCR', "")

                # Defines the port alias with the name of the radio (e.g. radioX_ssid_idY)
                if not empty(if_descr):
                    ports[port]['IFALIAS'] = if_descr
                # Replaces the radio port name with its respective <SSID>
                if_name = getCanonicalString(ai_wlan_essid_values.get(index))
                if not empty(if_name):
                    # radio0 and radio1 are the network interfaces for the 5GHz and 2.4GHz radios respectively
                    if 'radio0' in if_descr:
                        if_name += " (5GHz)"
                    elif 'radio1' in if_descr:
                        if_name += " (2.4GHz)"

                    ports[port]['IFNAME'] = if_name
                break

# Example usage to demonstrate functionality
if __name__ == "__main__":
    # Create a mock device
    device = Device()
    
    # Instantiate the Aruba SNMP support class
    aruba = GLPIAgentSNMPMibSupportAruba(device=device)
    
    # Test the methods
    print(f"Firmware: {aruba.get_firmware()}")
    print(f"Serial: {aruba.get_serial()}")
    print(f"Model: {aruba.get_model()}")
    
    # Run the inventory process
    aruba.run()
    
    # Display the updated ports
    print("Updated device ports:")
    for port, details in device.PORTS['PORT'].items():
        print(f"Port {port}: {details}")
