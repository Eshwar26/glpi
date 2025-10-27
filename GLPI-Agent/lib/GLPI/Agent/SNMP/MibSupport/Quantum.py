# quantum_mib.py
from typing import Optional, List, Dict
from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match, walk, trim_whitespace

ENTERPRISES = '.1.3.6.1.4.1'
QUANTUM = ENTERPRISES + '.3764'

# ADIC-INTELLIGENT-STORAGE-MIB
PRODUCT_AGENT_INFO = QUANTUM + '.1.1.10'
COMPONENTS = QUANTUM + '.1.1.30'

PRODUCT_MIB_VERSION = PRODUCT_AGENT_INFO + '.1.0'
PRODUCT_SNMP_AGENT_VERSION = PRODUCT_AGENT_INFO + '.2.0'
PRODUCT_NAME = PRODUCT_AGENT_INFO + '.3.0'
PRODUCT_VENDOR = PRODUCT_AGENT_INFO + '.6.0'
PRODUCT_SERIAL_NUMBER = PRODUCT_AGENT_INFO + '.10.0'

COMPONENT_TYPE = COMPONENTS + '.10.1.2'
COMPONENT_DISPLAY_NAME = COMPONENTS + '.10.1.3'
COMPONENT_SN = COMPONENTS + '.10.1.7'
COMPONENT_FIRMWARE_VERSION = COMPONENTS + '.10.1.11'
COMPONENT_IP_ADDRESS = COMPONENTS + '.10.1.17'


class Quantum(MibSupportTemplate):
    mib_support = [
        {"name": "quantum", "sysobjectid": get_regexp_oid_match(QUANTUM)}
    ]

    def get_firmware(self) -> Optional[str]:
        return get_canonical_string(self.get(PRODUCT_SNMP_AGENT_VERSION))

    @staticmethod
    def _index(key: str) -> int:
        import re
        match = re.search(r'(\d+)$', key)
        return int(match.group(1)) if match else 0

    def get_components(self) -> List[Dict]:
        device = self.device
        if not device:
            return []

        types_mapping = {
            1: "mcb",
            2: "cmb",
            3: "ioblade",
            4: "rcu",
            5: "chassis",
            6: "control",
            7: "expansion",
            8: "psu",
        }

        types = walk(COMPONENT_TYPE)
        names = walk(COMPONENT_DISPLAY_NAME)
        sns = walk(COMPONENT_SN)
        fws = walk(COMPONENT_FIRMWARE_VERSION)
        ips = walk(COMPONENT_IP_ADDRESS)

        components = []
        for key in sorted(types.keys(), key=lambda k: Quantum._index(k)):
            name = trim_whitespace(get_canonical_string(names.get(key, "")))
            serial = trim_whitespace(get_canonical_string(sns.get(key, "")))
            fw_version = trim_whitespace(get_canonical_string(fws.get(key, "")))
            type_str = types_mapping.get(types[key], "unknown")

            component = {
                "CONTAINEDININDEX": 0,
                "INDEX": Quantum._index(key),
                "NAME": name,
                "TYPE": type_str,
                "SERIAL": serial,
                "FIRMWARE": fw_version,
                "IP": trim_whitespace(get_canonical_string(ips.get(key, "")))
            }

            components.append(component)

            if fw_version:
                firmware = {
                    "NAME": name,
                    "DESCRIPTION": f"{name} version",
                    "TYPE": type_str,
                    "VERSION": fw_version,
                    "MANUFACTURER": device.get("MANUFACTURER")
                }
                device.add_firmware(firmware)

        # Add library unit
        if components:
            components.insert(0, {
                "CONTAINEDININDEX": -1,
                "INDEX": 0,
                "TYPE": "storage library",
                "NAME": f"{device.get('MANUFACTURER')} {device.get('MODEL')}"
            })

        return components

    def get_manufacturer(self) -> Optional[str]:
        return trim_whitespace(get_canonical_string(self.get(PRODUCT_VENDOR)))

    def get_model(self) -> Optional[str]:
        return get_canonical_string(self.get(PRODUCT_NAME))

    def get_serial(self) -> Optional[str]:
        return get_canonical_string(self.get(PRODUCT_SERIAL_NUMBER))

    @staticmethod
    def get_type() -> str:
        return "STORAGE"

    def run(self):
        device = self.device
        if not device:
            return

        mib_version = get_canonical_string(self.get(PRODUCT_MIB_VERSION))
        if mib_version:
            firmware = {
                "NAME": f"{device.get('MODEL')} MIB",
                "DESCRIPTION": f"{device.get('MODEL')} MIB version",
                "TYPE": "mib",
                "VERSION": mib_version,
                "MANUFACTURER": device.get("MANUFACTURER")
            }
            device.add_firmware(firmware)
