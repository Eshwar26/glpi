# panasas_mib.py
from typing import Optional

from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match, hex2char

# Panasas MIB constants
PANASAS = '.1.3.6.1.4.1.10159'
PAN_HW = PANASAS + '.1.2'
PAN_FS = PANASAS + '.1.3'

# PANASAS-SYSTEM-MIB-V1
PAN_CLUSTER_NAME = PAN_FS + '.2.1.1.0'
PAN_CLUSTER_MANAGEMENT_ADDRESS = PAN_FS + '.2.1.2.0'
PAN_CLUSTER_REPSET_ENTRY_IPADDR = PAN_FS + '.2.1.3.1.2'
PAN_CLUSTER_REPSET_ENTRY_BLADE_HW_SN = PAN_FS + '.2.1.3.1.3'


class Panasas(MibSupportTemplate):
    mib_support = [
        {"name": "panasas-panfs", "sysobjectid": get_regexp_oid_match(PAN_FS + '.0')}
    ]

    def get_serial(self) -> Optional[str]:
        device = self.device
        if not device:
            return None

        # Get the IP from session hostname or default to cluster management address
        ip = getattr(device, "snmp", None) and device.snmp.peer_address() \
            or self.get(PAN_CLUSTER_MANAGEMENT_ADDRESS)

        if not ip:
            return None

        # Find member IP index to select the related S/N
        cloud_ips = self.walk(PAN_CLUSTER_REPSET_ENTRY_IPADDR) or {}
        for index, member_ip in cloud_ips.items():
            if member_ip == ip:
                serial = self.get(f"{PAN_CLUSTER_REPSET_ENTRY_BLADE_HW_SN}.{index}")
                return hex2char(serial) if serial else None

    def run(self):
        device = self.device
        if not device:
            return

        name = self.get(PAN_CLUSTER_NAME)
        if name:
            device.INFO['NAME'] = get_canonical_string(name)
