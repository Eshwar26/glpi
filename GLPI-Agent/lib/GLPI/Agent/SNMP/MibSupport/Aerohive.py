import re
from typing import Dict, List, Any, Optional

# Mock utility functions to replace glpi_agent_tools
def getCanonicalString(value: Optional[str]) -> Optional[str]:
    """Mock implementation of getCanonicalString: Returns trimmed string or None."""
    if value is None or not str(value).strip():
        return None
    return str(value).strip()

# Mock utility function to replace glpi_agent_tools_snmp
def getRegexpOidMatch(oid: str) -> str:
    """Mock implementation of getRegexpOidMatch: Returns a regex pattern for the OID."""
    escaped_oid = re.escape(oid)
    return rf'^{escaped_oid}\..*'

# See AH-SMI-MIB
AEROHIVE = '.1.3.6.1.4.1.26928'
AH_PRODUCT = AEROHIVE + '.1'

# See AH-SYSTEM-MIB
AH_SYSTEM = AH_PRODUCT + '.2'
AH_SYSTEM_NAME = AH_SYSTEM + '.1.0'
AH_SYSTEM_SERIAL = AH_SYSTEM + '.5.0'
AH_DEVICE_MODE = AH_SYSTEM + '.6.0'
AH_HW_VERSION = AH_SYSTEM + '.8.0'
AH_FIRMWARE_VERSION = AH_SYSTEM + '.12.0'

MIB_SUPPORT = [
    {
        'name': "aerohive",
        'sysobjectid': getRegexpOidMatch(AEROHIVE)
    }
]

# Mock device class to simulate device interactions
class Device:
    def __init__(self):
        self.firmwares = []

    def add_firmware(self, firmware: Dict[str, str]):
        self.firmwares.append(firmware)
        print(f"Added firmware: {firmware}")

# Mock base class to simulate GLPIAgentSNMPMibSupportTemplate
class GLPIAgentSNMPMibSupportTemplate:
    def __init__(self, device: Optional[Device] = None):
        self.device = device
        self._snmp_data = {}  # Simulated SNMP data store

    def get(self, oid: str) -> Optional[str]:
        """Mock SNMP get operation."""
        # Simulate SNMP data for testing
        mock_data = {
            AH_SYSTEM_SERIAL: "AH123456789",
            AH_FIRMWARE_VERSION: "HiveOS 8.4r2",
            AH_DEVICE_MODE: "AP350",
            AH_HW_VERSION: "HW v1.2.3",
            AH_SYSTEM_NAME: "Aerohive-AP1"
        }
        return mock_data.get(oid)

class GLPIAgentSNMPMibSupportAerohive(GLPIAgentSNMPMibSupportTemplate):
    """
    Inventory module for Aerohive Networks

    This module enhances Aerohive Networks devices support.
    """

    @classmethod
    def get_type(cls):
        return 'NETWORKING'

    @classmethod
    def get_manufacturer(cls, self):
        return 'Aerohive Networks'

    @classmethod
    def get_serial(cls, self):
        return getCanonicalString(self.get(AH_SYSTEM_SERIAL))

    @classmethod
    def get_firmware(cls, self):
        return getCanonicalString(self.get(AH_FIRMWARE_VERSION))

    @classmethod
    def get_model(cls, self):
        return getCanonicalString(self.get(AH_DEVICE_MODE))

    def run(self):
        device = self.device
        if not device:
            return

        ah_hw_version = getCanonicalString(self.get(AH_HW_VERSION))
        if ah_hw_version:
            firmware = {
                'NAME': "Aerohive hardware",
                'DESCRIPTION': "Aerohive platform hardware version",
                'TYPE': "hardware",
                'VERSION': ah_hw_version,
                'MANUFACTURER': "Aerohive Networks"
            }
            device.add_firmware(firmware)

# Example usage to demonstrate functionality
if __name__ == "__main__":
    # Create a mock device
    device = Device()
    
    # Instantiate the Aerohive SNMP support class
    aerohive = GLPIAgentSNMPMibSupportAerohive(device=device)
    
    # Test the methods
    print(f"Type: {aerohive.get_type()}")
    print(f"Manufacturer: {aerohive.get_manufacturer(aerohive)}")
    print(f"Serial: {aerohive.get_serial(aerohive)}")
    print(f"Firmware: {aerohive.get_firmware(aerohive)}")
    print(f"Model: {aerohive.get_model(aerohive)}")
    
    # Run the inventory process
    aerohive.run()
    
    # Display the device's firmware list
    print(f"Device firmwares: {device.firmwares}")
