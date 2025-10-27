from typing import Optional, Dict, Any

from GLPI.Agent.SNMP.MibSupportTemplate import MibSupportTemplate
from GLPI.Agent.Tools import get_canonical_string, get_regexp_oid_match

# Oki MIB constants
OKI = '.1.3.6.1.4.1.2001'
MODEL = OKI + '.1.1.1.1.11.1.10.25.0'
SERIAL = OKI + '.1.1.1.1.11.1.10.45.0'

class Oki(MibSupportTemplate):
    mib_support = [
        {"name": "oki", "sysobjectid": get_regexp_oid_match(OKI)}
    ]

    def get_serial(self) -> Optional[str]:
        """Retrieve the serial number of the Oki device."""
        return self.get(SERIAL)

    def get_model(self) -> Optional[str]:
        """Retrieve the model name of the Oki device."""
        return get_canonical_string(self.get(MODEL))
