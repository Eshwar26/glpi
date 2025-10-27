# rnx_mib.py
from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match
import re

SYSDESCR = '.1.3.6.1.2.1.1.1.0'

# RNX-UPDU-MIB2-MIB
RNX = '.1.3.6.1.4.1.55108'
UPDU_MIB2 = RNX + '.2'

UPDU_MIB2_PDU_SERIAL_NUMBER = UPDU_MIB2 + '.1.2.1.5.1'
UPDU_MIB2_ICM_FIRMWARE = UPDU_MIB2 + '.6.2.1.9.1'


class RNX(MibSupportTemplate):
    mib_support = [
        {"name": "rnx-pdu", "sysobjectid": get_regexp_oid_match(RNX)}
    ]

    def get_manufacturer(self) -> str:
        return 'RNX'

    def get_serial(self) -> str:
        return get_canonical_string(self.get(UPDU_MIB2_PDU_SERIAL_NUMBER))

    def get_model(self) -> str:
        sysdescr = get_canonical_string(self.get(SYSDESCR))
        match = re.match(r'^RNX\s+(.*)\s+\(', sysdescr)
        if match:
            return match.group(1)
        return None

    def get_firmware(self) -> str:
        return get_canonical_string(self.get(UPDU_MIB2_ICM_FIRMWARE))
