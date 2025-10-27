"""
Enhanced Canon SNMP MIB Support Module
GLPI::Agent::SNMP::MibSupport::Canon - Inventory module for Canon printers
"""

import sys
import re
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING

# Attempt to import pysnmp.hlapi; if unavailable, provide minimal fallbacks
# so the module can be imported and linted without pysnmp installed.
if TYPE_CHECKING:
    from pysnmp.hlapi import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        ObjectType, ObjectIdentity, getCmd, nextCmd
    )
else:
    try:
        from pysnmp.hlapi import (
            SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
            ObjectType, ObjectIdentity, getCmd, nextCmd
        )
    except ImportError:
        # Minimal fallback stubs to avoid import errors when pysnmp is not available.
        # These stubs provide the same names used in the module but do not perform SNMP.
        class SnmpEngine:
            def __init__(self, *args, **kwargs): pass

        class CommunityData:
            def __init__(self, *args, **kwargs): pass

        class UdpTransportTarget:
            def __init__(self, *args, **kwargs): pass

        class ContextData:
            def __init__(self, *args, **kwargs): pass

        class ObjectIdentity:
            def __init__(self, *args, **kwargs): pass

        class ObjectType:
            def __init__(self, *args, **kwargs): pass

        def getCmd(*args, **kwargs):
            # Return a tuple to match expected callsite usage in fallback mode.
            return (None, None, None, [])

        def nextCmd(*args, **kwargs):
            # Return an empty iterator for walks when pysnmp is not present.
            return iter([])


class MibSupportTemplate:
    """Base template for SNMP MIB support implementations."""
    
    def __init__(self, host: str, community: str = 'public', port: int = 161, version: int = 1):
        """
        Initialize SNMP connection parameters.
        
        Args:
            host: Target device hostname or IP address
            community: SNMP community string (default: 'public')
            port: SNMP port (default: 161)
            version: SNMP version - 0 for v1, 1 for v2c (default: 1)
        """
        self.host = host
        self.community = community
        self.port = port
        self.version = version
        self.device: Dict[str, Any] = {}
        self.snmp_engine = SnmpEngine()
        self.comm_data = CommunityData(community, mpModel=version)
        self.transport = UdpTransportTarget((host, port), timeout=2.0, retries=3)
        self.context = ContextData()

    def _handle_snmp_error(
        self, 
        errorIndication: Any, 
        errorStatus: Any, 
        errorIndex: Any, 
        varBinds: List[Tuple]
    ) -> bool:
        """
        Handle SNMP errors and print appropriate messages.
        
        Returns:
            True if no errors occurred, False otherwise
        """
        if errorIndication:
            print(f"SNMP Error: {errorIndication}", file=sys.stderr)
            return False
        elif errorStatus:
            error_var = "?"
            if errorIndex and varBinds:
                try:
                    idx = int(errorIndex) - 1
                    if 0 <= idx < len(varBinds):
                        error_var = str(varBinds[idx][0])
                except (ValueError, IndexError, TypeError):
                    pass
            print(
                f'SNMP Error: {errorStatus.prettyPrint()} at {error_var}',
                file=sys.stderr
            )
            return False
        return True

    def get(self, oid: str) -> Optional[str]:
        """
        Perform SNMP GET for a single OID.
        
        Args:
            oid: Object Identifier to query
            
        Returns:
            String value of the OID or None if error/not found
        """
        try:
            errorIndication, errorStatus, errorIndex, varBinds = getCmd(
                self.snmp_engine,
                self.comm_data,
                self.transport,
                self.context,
                ObjectType(ObjectIdentity(oid))
            )
            
            if self._handle_snmp_error(errorIndication, errorStatus, errorIndex, varBinds):
                for varBind in varBinds:
                    value = varBind[1].prettyPrint()
                    return str(value) if value else None
        except Exception as e:
            print(f"Exception during SNMP GET {oid}: {e}", file=sys.stderr)
        
        return None

    def walk(self, oid: str) -> Optional[Dict[str, str]]:
        """
        Perform SNMP WALK starting from OID.
        
        Args:
            oid: Base Object Identifier to walk
            
        Returns:
            Dictionary mapping index to value, or None if error/empty
        """
        result = {}
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                self.snmp_engine,
                self.comm_data,
                self.transport,
                self.context,
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if not self._handle_snmp_error(errorIndication, errorStatus, errorIndex, varBinds):
                    break
                    
                for varBind in varBinds:
                    full_oid = str(varBind[0])
                    value = varBind[1].prettyPrint()
                    
                    # Extract index from full OID
                    if full_oid.startswith(oid + '.'):
                        index = full_oid[len(oid) + 1:]
                    else:
                        index = full_oid
                    
                    result[index] = str(value) if value else ""
        except Exception as e:
            print(f"Exception during SNMP WALK {oid}: {e}", file=sys.stderr)
            return None
        
        return result if result else None


def get_canonical_string(value: Optional[Any]) -> Optional[str]:
    """
    Convert value to canonical string format.
    
    Args:
        value: Input value to convert
        
    Returns:
        Stripped string or None if input is None/empty
    """
    if value is None:
        return None
    
    str_value = str(value).strip()
    return str_value if str_value else None


def hex2char(hexstr: Optional[str]) -> Optional[str]:
    """
    Convert hex string to character string.
    
    Args:
        hexstr: Hex string with format like "48 65 6c 6c 6f"
        
    Returns:
        Decoded string or None if conversion fails
    """
    if not hexstr:
        return None
    
    try:
        # Remove spaces and convert hex to bytes
        hex_clean = hexstr.replace(' ', '').replace('0x', '')
        decoded = bytes.fromhex(hex_clean).decode('utf-8', errors='ignore')
        return decoded.strip() if decoded else None
    except (ValueError, UnicodeDecodeError) as e:
        print(f"Hex conversion error for '{hexstr}': {e}", file=sys.stderr)
        return None


# SNMP OID Constants
ENTERPRISES = '.1.3.6.1.4.1'
CANON = ENTERPRISES + '.1602'
PPM_MIB = ENTERPRISES + '.2699.1.2'

# Canon Product Information
CAN_PRODUCT_INFO = CANON + '.1.1.1'
CAN_PD_INFO_PRODUCT_NAME = CAN_PRODUCT_INFO + '.1.0'
CAN_PD_INFO_PRODUCT_VERSION = CAN_PRODUCT_INFO + '.4.0'

# Canon Service Information
CAN_SERV_INFO_SERIAL_NUMBER_TABLE = CANON + '.1.2.1.8'
CAN_SERV_INFO_SERIAL_NUMBER_DEVICE_NUMBER = CAN_SERV_INFO_SERIAL_NUMBER_TABLE + '.1.3.1.1'

# Printer Port Monitor MIB
PPM_PRINTER = PPM_MIB + '.1.2'
PPM_PRINTER_NAME = PPM_PRINTER + '.1.1.2.1'

# Canon Counter OIDs
COUNTERS_C55XX = CANON + '.1.11.1.3.1.4'
TYPES_LPB76XX = CANON + '.1.11.2.1.1.2'
COUNTERS_LPB76XX = CANON + '.1.11.2.1.1.3'

# MIB support definition
mib_support = [
    {
        'name': 'canon',
        'sysobjectid': re.compile(r'^\.1\.3\.6\.1\.4\.1\.1602\.4\.')
    }
]


class Canon(MibSupportTemplate):
    """Canon printer SNMP support implementation."""
    
    def get_serial(self) -> Optional[str]:
        """
        Retrieve device serial number.
        
        Returns:
            Serial number string or None
        """
        serial = self.get(CAN_SERV_INFO_SERIAL_NUMBER_DEVICE_NUMBER)
        return get_canonical_string(serial)

    def get_firmware(self) -> Optional[str]:
        """
        Retrieve firmware version.
        
        Returns:
            Firmware version string or None
        """
        firmware = self.get(CAN_PD_INFO_PRODUCT_VERSION)
        return get_canonical_string(firmware)

    def get_model(self) -> Optional[str]:
        """
        Retrieve device model name.
        
        Returns:
            Model name string or None if already set or not found
        """
        if not self.device:
            return None

        # Don't override if already set
        if self.device.get('MODEL'):
            return None

        # Try Canon-specific OID first, then fall back to PPM MIB
        model = self.get(CAN_PD_INFO_PRODUCT_NAME)
        if not model:
            model = self.get(PPM_PRINTER_NAME)
        
        return get_canonical_string(model)

    def _process_c55xx_counters(self, counters: Dict[str, str]) -> None:
        """Process counters for C55XX series devices."""
        mapping = {
            '101': 'COPYTOTAL',
            '112': 'COPYBLACK',
            '113': 'COPYBLACK',
            '122': 'COPYCOLOR',
            '123': 'COPYCOLOR',
            '301': 'PRINTTOTAL',
            '501': 'SCANNED',
        }

        # Indices that should be added to existing values
        add_mapping = {'112', '113', '122', '123'}

        # Ensure PAGECOUNTERS exists
        if 'PAGECOUNTERS' not in self.device:
            self.device['PAGECOUNTERS'] = {}

        for index in sorted(counters.keys()):
            counter_name = mapping.get(index)
            if not counter_name:
                continue
            
            count_str = counters[index]
            if not count_str:
                continue
            
            try:
                count_int = int(count_str)
            except ValueError:
                print(f"Invalid counter value for index {index}: {count_str}", file=sys.stderr)
                continue
            
            # Add or set the counter value
            if index in add_mapping and counter_name in self.device['PAGECOUNTERS']:
                self.device['PAGECOUNTERS'][counter_name] += count_int
            else:
                self.device['PAGECOUNTERS'][counter_name] = count_int

    def _process_lpb76xx_counters(self, counters: Dict[str, str], types: Dict[str, str]) -> None:
        """Process counters for LPB76XX series devices."""
        mapping = {
            'Total 1': 'TOTAL',
            'Total (Black 1)': 'PRINTBLACK',
            'Total (Black/Large)': 'PRINTBLACK',
            'Total (Black/Small)': 'PRINTBLACK',
            'Total (Full Color + Single Color/Large)': 'PRINTCOLOR',
            'Total (Full Color + Single Color/Small)': 'PRINTCOLOR',
            'Print (Total 1)': 'PRINTTOTAL',
            'Copy (Total 1)': 'COPYTOTAL',
            'Scan (Total 1)': 'SCANNED',
        }

        # Types that should be added to existing values
        add_mapping = {
            'Total (Black/Large)',
            'Total (Black/Small)',
            'Total (Full Color + Single Color/Large)',
            'Total (Full Color + Single Color/Small)',
        }

        # Skip certain mappings if parent types exist
        skip_add_mapping = {
            'Total (Black 1)': ['Total (Black/Large)', 'Total (Black/Small)'],
        }

        # Ensure PAGECOUNTERS exists
        if 'PAGECOUNTERS' not in self.device:
            self.device['PAGECOUNTERS'] = {}

        for index in sorted(types.keys()):
            type_hex = types[index]
            type_val = hex2char(type_hex)
            
            if not type_val:
                continue
            
            counter_name = mapping.get(type_val)
            if not counter_name:
                continue
            
            count_str = counters.get(index)
            if not count_str:
                continue
            
            try:
                count_int = int(count_str)
            except ValueError:
                print(f"Invalid counter value for index {index}: {count_str}", file=sys.stderr)
                continue
            
            # Add or set the counter value
            if type_val in add_mapping and counter_name in self.device['PAGECOUNTERS']:
                self.device['PAGECOUNTERS'][counter_name] += count_int
            else:
                self.device['PAGECOUNTERS'][counter_name] = count_int
            
            # Remove skip mappings if parent exists
            if type_val in skip_add_mapping:
                for key in skip_add_mapping[type_val]:
                    mapping.pop(key, None)

    def run(self) -> None:
        """
        Main execution method to gather page counters.
        Tries C55XX format first, then falls back to LPB76XX format.
        """
        if not self.device:
            print("Device dictionary not initialized", file=sys.stderr)
            return

        # Ensure PAGECOUNTERS exists
        if 'PAGECOUNTERS' not in self.device:
            self.device['PAGECOUNTERS'] = {}

        # Try C55XX counters first
        counters = self.walk(COUNTERS_C55XX)
        if counters:
            self._process_c55xx_counters(counters)
            return

        # Fall back to LPB76XX counters
        counters = self.walk(COUNTERS_LPB76XX)
        if not counters:
            print("No counters found for this device", file=sys.stderr)
            return

        types = self.walk(TYPES_LPB76XX)
        if not types:
            print("Counter types not found for LPB76XX", file=sys.stderr)
            return

        self._process_lpb76xx_counters(counters, types)


def main():
    """Main function for standalone testing."""
    if len(sys.argv) < 2:
        print("Usage: python canon.py <host> [community] [port]")
        print("\nExample:")
        print("  python canon.py 192.168.1.100")
        print("  python canon.py 192.168.1.100 public")
        print("  python canon.py 192.168.1.100 public 161")
        sys.exit(1)

    host = sys.argv[1]
    community = sys.argv[2] if len(sys.argv) > 2 else 'public'
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 161

    print(f"Connecting to Canon printer at {host}:{port}")
    print(f"Community: {community}\n")

    # Initialize Canon SNMP client
    canon = Canon(host=host, community=community, port=port)
    canon.device = {'MODEL': None, 'PAGECOUNTERS': {}}

    # Retrieve device information
    print("=" * 50)
    print("DEVICE INFORMATION")
    print("=" * 50)
    
    serial = canon.get_serial()
    print(f"Serial Number: {serial if serial else 'Not available'}")
    
    firmware = canon.get_firmware()
    print(f"Firmware Version: {firmware if firmware else 'Not available'}")
    
    model = canon.get_model()
    if model:
        canon.device['MODEL'] = model
    print(f"Model: {canon.device.get('MODEL', 'Not available')}")
    
    print("\n" + "=" * 50)
    print("PAGE COUNTERS")
    print("=" * 50)
    print("Before retrieval:", canon.device.get('PAGECOUNTERS', {}))
    
    # Retrieve page counters
    canon.run()
    
    print("\nAfter retrieval:")
    if canon.device.get('PAGECOUNTERS'):
        for counter_name, counter_value in sorted(canon.device['PAGECOUNTERS'].items()):
            print(f"  {counter_name}: {counter_value:,}")
    else:
        print("  No counters retrieved")
    
    print("\n" + "=" * 50)
    print("Module executed successfully")
    print("=" * 50)


if __name__ == "__main__":
    main()
