# mikrotik_mib.py
import re
from typing import Optional

from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_regexp_oid_match

# MIKROTIK-MIB constants
MIKROTIK_EXPERIMENTAL_MODULE = '.1.3.6.1.4.1.14988.1'
MTXR_SYSTEM = MIKROTIK_EXPERIMENTAL_MODULE + '.1.7'

MTXR_SERIAL_NUMBER = MTXR_SYSTEM + '.3.0'
MTXR_FIRMWARE_VERSION = MTXR_SYSTEM + '.4.0'


class Mikrotik(MibSupportTemplate):
    mib_support = [
        {
            "name": "mikrotik",
            "sysobjectid": get_regexp_oid_match(MIKROTIK_EXPERIMENTAL_MODULE),
        }
    ]

    def get_firmware(self) -> Optional[str]:
        """Return the firmware version of the Mikrotik device."""
        return self.get(MTXR_FIRMWARE_VERSION)

    def get_serial(self) -> Optional[str]:
        """Return the serial number of the Mikrotik device."""
        return self.get(MTXR_SERIAL_NUMBER)

    def get_model(self) -> Optional[str]:
        """
        Extract the model from the device DESCRIPTION if it matches RouterOS.
        """
        device = self.device
        if not device:
            return None

        model = None
        description = device.get("DESCRIPTION")
        if description:
            match = re.match(r"^RouterOS\s+(.*)$", description)
            if match:
                model = match.group(1)

        return model
