# qnap_mib.py
from typing import Optional
from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_regexp_oid_match

# Constants
PRIORITY = 5

# NAS-MIB
QNAP_STORAGE = '.1.3.6.1.4.1.24681'
ES_STORAGE_SYSTEM = QNAP_STORAGE + '.2'
ES_SYSTEM_INFO = ES_STORAGE_SYSTEM + '.2'
ES_MODEL_NAME = ES_SYSTEM_INFO + '.12.0'
ES_HOST_NAME = ES_SYSTEM_INFO + '.13.0'


class Qnap(MibSupportTemplate):
    mib_support = [
        {"name": "qnap-storage", "sysobjectid": QNAP_STORAGE},
        {"name": "qnap-model", "privateoid": ES_MODEL_NAME}
    ]

    @staticmethod
    def get_type() -> str:
        return 'STORAGE'

    def get_model(self) -> Optional[str]:
        return self.get(ES_MODEL_NAME)

    @staticmethod
    def get_manufacturer() -> str:
        return 'Qnap'
