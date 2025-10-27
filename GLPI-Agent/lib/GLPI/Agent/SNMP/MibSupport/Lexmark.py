# lexmark_mib_support.py
# Converted from Perl: GLPI::Agent::SNMP::MibSupport::Lexmark

from glpi_agent.tools import get_canonical_string, get_regexp_oid_match
from glpi_agent.tools.snmp import SNMPBase

# ---------------------------
# OID CONSTANTS
# ---------------------------
ENTERPRISES = ".1.3.6.1.4.1"

# LEXMARK-ROOT-MIB
LEXMARK = f"{ENTERPRISES}.641"

# LEXMARK-PVT-MIB
PRINTER = f"{LEXMARK}.2"
PRTGEN_INFO_ENTRY = f"{PRINTER}1.2.1"

PRTGEN_PRINTER_NAME = f"{PRTGEN_INFO_ENTRY}.2.1"
PRTGEN_CODE_REVISION = f"{PRTGEN_INFO_ENTRY}.4.1"
PRTGEN_SERIAL_NO = f"{PRTGEN_INFO_ENTRY}.6.1"

# LEXMARK-MPS-MIB
MPS = f"{LEXMARK}.6"

DEVICE = f"{MPS}.2"
INVENTORY = f"{MPS}.3"

DEVICE_MODEL = f"{DEVICE}.3.1.4.1"
DEVICE_SERIAL = f"{DEVICE}.3.1.5.1"

HW_INVENTORY_SERIAL_NUMBER = f"{INVENTORY}.1.1.7.1.1"
SW_INVENTORY_REVISION = f"{INVENTORY}.3.1.7.1.1"

# Printer-MIB
PRT_GENERAL_SERIAL_NUMBER = ".1.3.6.1.2.1.43.5.1.1.17.1"

# HOST-RESOURCES-MIB
HR_DEVICE_DESCR = ".1.3.6.1.2.1.25.3.2.1.3.1"

# ---------------------------
# MIB SUPPORT REGISTRATION
# ---------------------------
MIB_SUPPORT = [
    {
        "name": "lexmark-printer",
        "sysobjectid": get_regexp_oid_match(LEXMARK),
    }
]


class LexmarkMibSupport(SNMPBase):
    """
    Python equivalent of GLPI::Agent::SNMP::MibSupport::Lexmark

    Enhances SNMP inventory for Lexmark printer devices.
    """

    def get_model(self):
        """
        Retrieves the printer model name, removing manufacturer prefixes if present.
        """
        model = None
        for oid in (DEVICE_MODEL, PRTGEN_PRINTER_NAME):
            value = self.get(oid)
            if value:
                model = get_canonical_string(value)
                if model:
                    break

        if not model:
            value = self.get(HR_DEVICE_DESCR)
            if not value:
                return None
            model_str = get_canonical_string(value)
            if model_str:
                # Extract "Lexmark <something>" substring
                import re
                match = re.match(r"^(Lexmark\s+\S+)", model_str)
                if match:
                    model = match.group(1)

        if not model:
            return None

        # Remove "Lexmark" prefix if present
        model = model.replace("Lexmark ", "", 1).strip()
        return model

    def get_firmware(self):
        """
        Retrieves the printer firmware version from known OIDs.
        """
        for oid in (SW_INVENTORY_REVISION, PRTGEN_CODE_REVISION):
            value = self.get(oid)
            if value:
                firmware = get_canonical_string(value)
                if firmware:
                    return firmware
        return None

    def get_serial(self):
        """
        Retrieves the printer serial number from multiple fallback OIDs.
        """
        for oid in (PRT_GENERAL_SERIAL_NUMBER, DEVICE_SERIAL, PRTGEN_SERIAL_NO):
            value = self.get(oid)
            if value:
                serial = get_canonical_string(value)
                if serial:
                    return serial
        return None
