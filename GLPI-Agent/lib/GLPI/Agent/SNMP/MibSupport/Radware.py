# radware_mib.py
from glpi_agent_snmp_template import MibSupportTemplate
from glpi_agent_tools import get_canonical_string, get_regexp_oid_match, get_canonical_mac_address

ENTERPRISES = '.1.3.6.1.4.1'

# ALTEON-ROOT-MIB
ALTEON = ENTERPRISES + '.1872'
AWSSWITCH = ALTEON + '.2.5'

# ALTEON-CHEETAH-SWITCH-MIB
AGENT = AWSSWITCH + '.1'
AGENT_CONFIG = AGENT + '.1'
AGENT_INFO = AGENT + '.3'

AG_SYSTEM = AGENT_CONFIG + '.1'
AG_MGMT = AGENT_CONFIG + '.9'

HARDWARE = AGENT_INFO + '.1'

AG_PLATFORM_IDENTIFIER = AG_SYSTEM + ".77.0"
AG_MGMT_CUR_CFG_IPADDR = AG_MGMT + ".1.0"

HW_MAINBOARD_NUMBER = HARDWARE + '.6.0'
HW_MAINBOARD_REVISION = HARDWARE + '.7.0'
HW_MAC_ADDRESS = HARDWARE + '.13.0'
HW_SERIAL_NUMBER = HARDWARE + '.18.0'
HW_PLD_FIRMWARE_VERSION = HARDWARE + '.21.0'
HW_VERSION = HARDWARE + '.30.0'


class Radware(MibSupportTemplate):
    mib_support = [
        {"name": "alteon-radware", "sysobjectid": get_regexp_oid_match(ALTEON)}
    ]

    def get_firmware(self) -> str:
        return get_canonical_string(self.get(HW_PLD_FIRMWARE_VERSION))

    def get_ip(self) -> str:
        device = self.device
        if device.IPS:
            return None
        ip = get_canonical_string(self.get(AG_MGMT_CUR_CFG_IPADDR))
        return ip

    def get_manufacturer(self) -> str:
        device = self.device
        if device.MANUFACTURER:
            return None
        return "Radware"

    def get_model(self) -> str:
        model = get_canonical_string(self.get(AG_PLATFORM_IDENTIFIER))
        return f"Alteon {model}"

    def get_serial(self) -> str:
        return get_canonical_string(self.get(HW_SERIAL_NUMBER))

    def run(self):
        device = self.device

        mbnum = get_canonical_string(self.get(HW_MAINBOARD_NUMBER))
        mbrev = get_canonical_string(self.get(HW_MAINBOARD_REVISION))
        if mbnum and mbrev:
            firmware = {
                "NAME": f"{device.MODEL} {mbnum} mainboard",
                "DESCRIPTION": f"{device.MODEL} {mbnum} mainboard revision",
                "TYPE": "mainboard",
                "VERSION": mbrev,
                "MANUFACTURER": "Radware"
            }
            device.add_firmware(firmware)

        hw_version = get_canonical_string(self.get(HW_VERSION))
        if hw_version:
            firmware = {
                "NAME": f"{device.MODEL} hardware",
                "DESCRIPTION": f"{device.MODEL} hardware revision",
                "TYPE": "device",
                "VERSION": hw_version,
                "MANUFACTURER": "Radware"
            }
            device.add_firmware(firmware)

        if not device.MAC:
            device.MAC = get_canonical_mac_address(self.get(HW_MAC_ADDRESS))
            device.INFO["MAC"] = device.MAC
