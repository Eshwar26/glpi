# raritan_mib.py
from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match

RARITAN = '.1.3.6.1.4.1.13742'
PDU2 = RARITAN + '.6'

NAMEPLATE_ENTRY = PDU2 + '.3.2.1.1'
PDU_MANUFACTURER = NAMEPLATE_ENTRY + '.2.1'
PDU_MODEL = NAMEPLATE_ENTRY + '.3.1'
PDU_SERIAL_NUMBER = NAMEPLATE_ENTRY + '.4.1'

UNIT_CONFIGURATION_ENTRY = PDU2 + '.3.2.2.1'
PDU_NAME = UNIT_CONFIGURATION_ENTRY + '.13.1'


class Raritan(MibSupportTemplate):
    mib_support = [
        {"name": "raritan-pdu2", "sysobjectid": get_regexp_oid_match(PDU2)}
    ]

    def get_manufacturer(self) -> str:
        return get_canonical_string(self.get(PDU_MANUFACTURER)) or "Raritan"

    def get_serial(self) -> str:
        return get_canonical_string(self.get(PDU_SERIAL_NUMBER))

    def get_model(self) -> str:
        return get_canonical_string(self.get(PDU_MODEL))

    def get_snmp_hostname(self) -> str:
        return get_canonical_string(self.get(PDU_NAME))
