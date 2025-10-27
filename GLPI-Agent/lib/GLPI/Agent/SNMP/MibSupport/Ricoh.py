# ricoh_mib.py
from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match

MIB2 = '.1.3.6.1.2.1'
ENTERPRISES = '.1.3.6.1.4.1'

# Ricoh-Private-MIB
RICOH = ENTERPRISES + '.367'
RICOH_AGENTS_ID = RICOH + '.1.1'
RICOH_NET_CONT = RICOH + '.3.2.1.6'

RICOH_ENG_COUNTER = RICOH + '.3.2.1.2.19'
RICOH_ENG_COUNTER_TYPE = RICOH_ENG_COUNTER + '.5.1.2'
RICOH_ENG_COUNTER_VALUE = RICOH_ENG_COUNTER + '.5.1.9'

HOSTNAME = RICOH_NET_CONT + '.1.1.7.1'

# Printer-MIB
PRINTMIB = MIB2 + '.43'
PRT_GENERAL_PRINTER_NAME = PRINTMIB + '.5.1.1.16.1'


class Ricoh(MibSupportTemplate):
    mib_support = [
        {"name": "ricoh-printer", "sysobjectid": get_regexp_oid_match(RICOH_AGENTS_ID)}
    ]

    def get_model(self) -> str:
        return self.get(PRT_GENERAL_PRINTER_NAME)

    def get_snmp_hostname(self) -> str:
        device = self.device
        hostname = get_canonical_string(self.get(HOSTNAME))

        # Don't override if found hostname is manufacturer+model
        if hostname == f"RICOH {device.MODEL}":
            return None

        return hostname

    def run(self):
        device = self.device

        types = self.walk(RICOH_ENG_COUNTER_TYPE)
        counters = self.walk(RICOH_ENG_COUNTER_VALUE) or {}

        mapping = {
            10: 'TOTAL',
            200: 'COPYTOTAL',
            201: 'COPYBLACK',
            202: 'COPYCOLOR',
            203: 'COPYCOLOR',
            300: 'FAXTOTAL',
            400: 'PRINTTOTAL',
            401: 'PRINTBLACK',
            402: 'PRINTCOLOR',
            403: 'PRINTCOLOR',
            870: 'SCANNED',
            871: 'SCANNED',
        }

        add_mapping = {202, 203, 402, 403, 870, 871}

        for index in sorted(types.keys()):
            type_id = types[index]
            counter_name = mapping.get(type_id)
            if not counter_name:
                continue

            count = counters.get(index)
            if not count:
                continue

            if type_id in add_mapping and device.PAGECOUNTERS.get(counter_name):
                device.PAGECOUNTERS[counter_name] += count
            else:
                device.PAGECOUNTERS[counter_name] = count
