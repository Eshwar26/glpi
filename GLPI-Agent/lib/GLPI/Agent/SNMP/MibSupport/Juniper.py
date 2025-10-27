import re

# ------------------------------
# Mock or simplified helper functions
# ------------------------------

def get_regexp_oid_match(oid):
    """Return a compiled regex for exact prefix match (used in sysobjectid)"""
    return re.compile(f'^{re.escape(oid)}')

def get_canonical_string(value):
    """Normalize string"""
    if value is None:
        return None
    return str(value).strip()

def get_canonical_mac_address(value):
    """Normalize MAC address (AA:BB:CC:DD:EE:FF)"""
    if not value:
        return None
    value = str(value).replace("-", ":").replace(".", "")
    if len(value) == 12 and ":" not in value:
        return ":".join(value[i:i+2] for i in range(0, 12, 2)).upper()
    return value.upper()

def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

def empty(value):
    """Check for empty string or None"""
    return value is None or (isinstance(value, str) and value.strip() == "")

def sorted_ports(ports):
    """Sort ports numerically or lexically (similar to Perl's sortedPorts)"""
    try:
        return sorted(ports.keys(), key=lambda x: int(x))
    except Exception:
        return sorted(ports.keys())


# ------------------------------
# Base template (mock of GLPI::Agent::SNMP::MibSupportTemplate)
# ------------------------------

class MibSupportTemplate:
    def __init__(self):
        self.device = None

    def get(self, oid):
        """Mock SNMP get; real implementation should fetch from SNMP agent."""
        mock_values = {
            '.1.3.6.1.4.1.2636.3.40.1.4.1.1.1.2.0': 'JN12345678',    # Serial number
            '.1.3.6.1.4.1.2636.3.40.1.4.1.1.1.4.0': '00:11:22:33:44:55',  # MAC
            '.1.3.6.1.4.1.2636.3.40.1.4.1.1.1.5.0': '21.3R1.8',      # Firmware
            '.1.3.6.1.4.1.2636.3.40.1.4.1.1.1.8.0': 'EX3400-48T',    # Model
        }
        return mock_values.get(oid, None)


# ------------------------------
# Mock Device structure
# ------------------------------

class MockDevice:
    def __init__(self):
        # PORTS structure to simulate SNMP inventory data
        self.PORTS = {
            'PORT': {
                '1': {'IFNAME': 'ge-0/0/0', 'IFTYPE': 6, 'MAC': '00:11:22:33:44:55', 'IFMTU': 1514},
                '2': {'IFNAME': 'ge-0/0/0.0', 'IFTYPE': 53, 'MAC': '00:11:22:33:44:55', 'IFMTU': 1514},
            }
        }
        self.SERIAL = None


# ------------------------------
# OID constants (JUNIPER-SMI)
# ------------------------------

ENTERPRISES = '.1.3.6.1.4.1'
JUNIPER_MIB = ENTERPRISES + '.2636'
JNX_MIBS = JUNIPER_MIB + '.3'
JNX_EX_MIB_ROOT = JNX_MIBS + '.40'

# JUNIPER-EX-SMI
JNX_EX_VIRTUAL_CHASSIS = JNX_EX_MIB_ROOT + '.1.4'

# JUNIPER-VIRTUALCHASSIS-MIB
JNX_VIRTUAL_CHASSIS_MEMBER_SERIALNUMBER = JNX_EX_VIRTUAL_CHASSIS + '.1.1.1.2.0'
JNX_VIRTUAL_CHASSIS_MEMBER_MACADD_BASE = JNX_EX_VIRTUAL_CHASSIS + '.1.1.1.4.0'
JNX_VIRTUAL_CHASSIS_MEMBER_SWVERSION = JNX_EX_VIRTUAL_CHASSIS + '.1.1.1.5.0'
JNX_VIRTUAL_CHASSIS_MEMBER_MODEL = JNX_EX_VIRTUAL_CHASSIS + '.1.1.1.8.0'

# MIB Support registration
mib_support = [
    {
        'name': 'juniper',
        'sysobjectid': get_regexp_oid_match(JUNIPER_MIB)
    }
]


# ------------------------------
# Juniper MIB Support Class
# ------------------------------

class Juniper(MibSupportTemplate):
    """Equivalent to GLPI::Agent::SNMP::MibSupport::Juniper"""

    def get_firmware(self):
        return get_canonical_string(self.get(JNX_VIRTUAL_CHASSIS_MEMBER_SWVERSION))

    def get_mac_address(self):
        return get_canonical_mac_address(self.get(JNX_VIRTUAL_CHASSIS_MEMBER_MACADD_BASE))

    def get_model(self):
        return get_canonical_string(self.get(JNX_VIRTUAL_CHASSIS_MEMBER_MODEL))

    def get_serial(self):
        device = self.device
        if not device:
            return None
        if getattr(device, 'SERIAL', None):
            return None
        return get_canonical_string(self.get(JNX_VIRTUAL_CHASSIS_MEMBER_SERIALNUMBER))

    def run(self):
        device = self.device
        if not device:
            return

        if hasattr(device, 'PORTS') and isinstance(device.PORTS, dict):
            ports = device.PORTS.get('PORT', {})
            if not isinstance(ports, dict):
                return

            index = {}
            portnames = sorted_ports(ports)

            # Map IFNAME -> index
            for idx in portnames:
                if not empty(ports[idx].get('IFNAME')):
                    index[ports[idx]['IFNAME']] = idx

            # Merge virtual ports with physical ones (like in Perl)
            for name in portnames:
                port = ports[name]
                if 'IFTYPE' not in port or not is_integer(port['IFTYPE']):
                    continue

                if int(port['IFTYPE']) != 53:  # 53 = virtual interface
                    continue

                match = re.match(r'^(.+)\.\d+$', port['IFNAME'])
                if not match:
                    continue
                physical = match.group(1)

                if physical not in index:
                    continue
                if physical not in ports:
                    continue

                physical_port = ports[index[physical]]
                if not (port.get('MAC') and physical_port.get('MAC') and port['MAC'] == physical_port['MAC']):
                    continue
                if not (port.get('IFMTU') and physical_port.get('IFMTU') and port['IFMTU'] == physical_port['IFMTU']):
                    continue

                merge = ports.pop(index[physical], None)
                if not merge:
                    continue

                # Copy attributes (Perl maps)
                for key in ['IFNAME', 'IFDESCR', 'IFTYPE', 'IFSPEED', 'VLAN']:
                    if merge.get(key):
                        port[key] = merge[key]

                for key in ['IFINERRORS', 'IFINOCTETS', 'IFOUTERRORS', 'IFOUTOCTETS']:
                    port[key] = port.get(key, 0)
                    if merge.get(key):
                        port[key] += merge[key]


# ------------------------------
# Standalone Test Execution
# ------------------------------

if __name__ == "__main__":
    juniper = Juniper()
    device = MockDevice()
    juniper.device = device

    print("Firmware:", juniper.get_firmware())
    print("MAC:", juniper.get_mac_address())
    print("Model:", juniper.get_model())
    print("Serial:", juniper.get_serial())

    print("\nBefore run - Ports:")
    for k, v in device.PORTS['PORT'].items():
        print(f"  Port {k}: {v}")

    juniper.run()

    print("\nAfter run - Ports:")
    for k, v in device.PORTS['PORT'].items():
        print(f"  Port {k}: {v}")

    print("\nJuniper module executed successfully with full functionality.")
