# kyocera_mib_support.py
# Converted from Perl: GLPI::Agent::SNMP::MibSupport::Kyocera

def get_canonical_string(value):
    """Convert value to canonical string format"""
    if not value:
        return None
    # Remove leading/trailing whitespace and normalize spaces
    return ' '.join(str(value).strip().split())

def get_regexp_oid_match(oid):
    """Convert OID to regex pattern for matching"""
    if not oid:
        return None
    # Escape dots in OID and add regex pattern
    return '^' + oid.replace('.', '\\.') + '.*'
class SNMPBase:
    """
    Base class for SNMP support implementations
    Basic implementation of common SNMP functionality
    """
    def __init__(self):
        self.data = {}

    def get(self, oid):
        """Get SNMP value for given OID"""
        return self.data.get(oid)

# Constants equivalent to Perl's `use constant`
PRIORITY = 7

KYOCERA = ".1.3.6.1.4.1.1347"
SYSNAME = f"{KYOCERA}.40.10.1.1.5.1"
KYOCERA_PRINTER = f"{KYOCERA}.41"

# MIB support definition
MIB_SUPPORT = [
    {
        "name": "kyocera",
        "sysobjectid": get_regexp_oid_match(KYOCERA_PRINTER),
    }
]


class KyoceraMibSupport(SNMPBase):
    """
    Python equivalent of GLPI::Agent::SNMP::MibSupport::Kyocera

    Provides SNMP inventory support for Kyocera printers.
    """

    priority = PRIORITY

    def get_snmp_hostname(self):
        """Retrieve and normalize the SNMP system name."""
        sys_name = self.get(SYSNAME)
        return get_canonical_string(sys_name) if sys_name else None
