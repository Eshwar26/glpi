# multitech_mib.py
from typing import Optional

from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string

# Multitech MIB constants
MULTITECH = '.1.3.6.1.4.1.995'
MTS_ROUTER_SYSTEM_OBJECTS = MULTITECH + '.15.1.1'

MTS_ROUTER_SYSTEM_MODEL_ID = MTS_ROUTER_SYSTEM_OBJECTS + '.1.0'
MTS_ROUTER_SYSTEM_SERIAL_NUMBER = MTS_ROUTER_SYSTEM_OBJECTS + '.2.0'
MTS_ROUTER_SYSTEM_FIRMWARE = MTS_ROUTER_SYSTEM_OBJECTS + '.3.0'


class Multitech(MibSupportTemplate):
    mib_support = [
        {
            "name": "multitech",
            "privateoid": MTS_ROUTER_SYSTEM_MODEL_ID,
        }
    ]

    def get_serial(self) -> Optional[str]:
        """Return the serial number of the Multitech device."""
        return get_canonical_string(self.get(MTS_ROUTER_SYSTEM_SERIAL_NUMBER))

    def get_snmp_hostname(self) -> Optional[str]:
        """Compute a hostname based on MODEL and serial number."""
        serial = self.get_serial()
        if not serial:
            return None

        device = self.device
        if not device:
            return None

        model = device.get("MODEL")
        return f"{model}_{serial}" if model else serial

    def get_model(self) -> Optional[str]:
        """Return the device model."""
        return get_canonical_string(self.get(MTS_ROUTER_SYSTEM_MODEL_ID))

    def get_firmware(self) -> Optional[str]:
        """Return the firmware version."""
        return self.get(MTS_ROUTER_SYSTEM_FIRMWARE)

    def get_type(self) -> str:
        """Return the type of device."""
        return "NETWORKING"

    def get_manufacturer(self) -> str:
        """Return the manufacturer."""
        return "Multitech"
    def run(self):
        device = self.device
        if not device:
            return
