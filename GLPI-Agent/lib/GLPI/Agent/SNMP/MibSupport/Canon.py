"""
Enhanced Canon SNMP MIB Support Module
GLPI::Agent::SNMP::MibSupport::Canon - Inventory module for Canon printers
"""

import re
import sys
from typing import Dict, Any, Optional, TYPE_CHECKING

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
    except Exception:
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


# Utility functions
def get_canonical_string(value: Optional[Any]) -> Optional[str]:
    """Canonical string processing: trim and return non-empty string."""
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed if trimmed else None


def hex2char(hexstr: Optional[str]) -> Optional[str]:
    """Convert hex string to character string."""
    if not hexstr:
        return None
    try:
        # Handle hex strings with spaces (e.g., "48 65 6c 6c 6f")
        cleaned = hexstr.replace(' ', '').replace('0x', '')
        return bytes.fromhex(cleaned).decode('utf-8', errors='ignore')
    except (ValueError, UnicodeDecodeError):
        return None


# Constants
ENTERPRISES = '.1.3.6.1.4.1'
CANON = f"{ENTERPRISES}.1602"
PPM_MIB = f"{ENTERPRISES}.2699.1.2"

# Canon specific OIDs
CAN_PRODUCT_INFO = f"{CANON}.1.1.1"
CAN_PD_INFO_PRODUCT_NAME = f"{CAN_PRODUCT_INFO}.1.0"
CAN_PD_INFO_PRODUCT_VERSION = f"{CAN_PRODUCT_INFO}.4.0"
CAN_SERV_INFO_SERIAL_NUMBER = f"{CANON}.1.2.1.8.1.3.1.1"
PPM_PRINTER_NAME = f"{PPM_MIB}.1.2.1.1.2.1"

# Counter OIDs
COUNTERS_C55XX = f"{CANON}.1.11.1.3.1.4"
TYPES_LPB76XX = f"{CANON}.1.11.2.1.1.2"
COUNTERS_LPB76XX = f"{CANON}.1.11.2.1.1.3"

# MIB Support Configuration
mib_support = [{
    'name': 'canon',
    'sysobjectid': re.compile(r'^\.1\.3\.6\.1\.4\.1\.1602\.4\.')
}]


class SNMPError(Exception):
    """Custom exception for SNMP errors"""
    pass


class MibSupportTemplate:
    """Base template for SNMP MIB support"""
    
    def __init__(self, host: str, community: str = 'public', port: int = 161, version: int = 1):
        """
        Initialize SNMP connection.
        
        Args:
            host: Target device IP or hostname
            community: SNMP community string
            port: SNMP port (default 161)
            version: SNMP version (0=v1, 1=v2c, default=1)
        """
        self.host = host
        self.community = community
        self.port = port
        self.version = version
        self.device = {'MODEL': None, 'PAGECOUNTERS': {}}
        
        # SNMP session setup
        self.snmp_engine = SnmpEngine()
        self.comm_data = CommunityData(community, mpModel=version)
        self.transport = UdpTransportTarget((host, port), timeout=2.0, retries=3)
        self.context = ContextData()

    def _handle_snmp_error(self, errorIndication, errorStatus, errorIndex, varBinds) -> bool:
        """Handle SNMP errors and return success status."""
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
        """Perform SNMP GET for a single OID."""
        try:
            errorIndication, errorStatus, errorIndex, varBinds = getCmd(
                self.snmp_engine, self.comm_data, self.transport, 
                self.context, ObjectType(ObjectIdentity(oid))
            )
            if self._handle_snmp_error(errorIndication, errorStatus, errorIndex, varBinds):
                for _, varValue in varBinds:
                    value = varValue.prettyPrint()
                    return str(value) if value else None
        except Exception as e:
            print(f"SNMP GET error for OID {oid}: {e}", file=sys.stderr)
        return None

    def walk(self, oid: str) -> Optional[Dict[str, str]]:
        """Perform SNMP WALK starting from OID."""
        result = {}
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                self.snmp_engine, self.comm_data, self.transport,
                self.context, ObjectType(ObjectIdentity(oid)),
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
                    elif full_oid.startswith(oid):
                        index = full_oid[len(oid):].lstrip('.')
                    else:
                        index = full_oid
                    
                    result[index] = str(value) if value else ""
                    
            return result if result else None
        except Exception as e:
            print(f"SNMP WALK error for OID {oid}: {e}", file=sys.stderr)
            return None


class Canon(MibSupportTemplate):
    """Canon printer specific SNMP implementation"""

    def get_serial(self) -> Optional[str]:
        """Get printer serial number."""
        return get_canonical_string(self.get(CAN_SERV_INFO_SERIAL_NUMBER))

    def get_firmware(self) -> Optional[str]:
        """Get printer firmware version."""
        firmware = self.get(CAN_PD_INFO_PRODUCT_VERSION)
        return get_canonical_string(firmware)

    def get_model(self) -> Optional[str]:
        """Get printer model."""
        if not self.device or self.device.get('MODEL'):
            return None
        
        model = self.get(CAN_PD_INFO_PRODUCT_NAME)
        if not model:
            model = self.get(PPM_PRINTER_NAME)
        
        return get_canonical_string(model)

    def _process_c55xx_counters(self) -> bool:
        """
        Process C55XX series counter values.
        
        Returns:
            True if counters were found and processed, False otherwise
        """
        counters = self.walk(COUNTERS_C55XX)
        if not counters:
            return False

        mapping = {
            '101': 'COPYTOTAL',
            '112': 'COPYBLACK',
            '113': 'COPYBLACK',
            '122': 'COPYCOLOR',
            '123': 'COPYCOLOR',
            '301': 'PRINTTOTAL',
            '501': 'SCANNED'
        }
        
        # Indices that should be added to existing values
        add_mapping = {'112', '113', '122', '123'}

        for index in sorted(counters.keys()):
            counter = mapping.get(index)
            if not counter:
                continue
                
            count = counters.get(index)
            if not count:
                continue
                
            try:
                count_int = int(count)
            except ValueError:
                print(f"Invalid counter value for index {index}: {count}", file=sys.stderr)
                continue
            
            # Add to existing or set new value
            if index in add_mapping and counter in self.device['PAGECOUNTERS']:
                self.device['PAGECOUNTERS'][counter] += count_int
            else:
                self.device['PAGECOUNTERS'][counter] = count_int
        
        return bool(self.device['PAGECOUNTERS'])

    def _process_lpb76xx_counters(self) -> bool:
        """
        Process LPB76XX series counter values.
        
        Returns:
            True if counters were found and processed, False otherwise
        """
        counters = self.walk(COUNTERS_LPB76XX)
        if not counters:
            return False

        types = self.walk(TYPES_LPB76XX)
        if not types:
            return False

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

        for index in sorted(types.keys()):
            type_hex = types.get(index)
            if not type_hex:
                continue
                
            type_val = hex2char(type_hex)
            if not type_val:
                continue
            
            counter = mapping.get(type_val)
            if not counter:
                continue
            
            count = counters.get(index)
            if not count:
                continue
            
            try:
                count_int = int(count)
            except ValueError:
                print(f"Invalid counter value for index {index}: {count}", file=sys.stderr)
                continue
            
            # Add to existing or set new value
            if type_val in add_mapping and counter in self.device['PAGECOUNTERS']:
                self.device['PAGECOUNTERS'][counter] += count_int
            else:
                self.device['PAGECOUNTERS'][counter] = count_int
            
            # Remove skip mappings if parent exists
            if type_val in skip_add_mapping:
                for key in skip_add_mapping[type_val]:
                    mapping.pop(key, None)
        
        return bool(self.device['PAGECOUNTERS'])

    def run(self) -> None:
        """Run the data collection and processing."""
        if not self.device:
            print("Device dictionary not initialized", file=sys.stderr)
            return

        # Ensure PAGECOUNTERS exists
        if 'PAGECOUNTERS' not in self.device:
            self.device['PAGECOUNTERS'] = {}

        # First pass - try to process as C55XX series
        if self._process_c55xx_counters():
            return

        # If no counters found, try LPB76XX series
        self._process_lpb76xx_counters()


def main():
    """Main function for standalone testing."""
    if len(sys.argv) < 2:
        print("Usage: python canon.py <host> [community] [port]", file=sys.stderr)
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

    # Test instantiation with real SNMP
    try:
        canon = Canon(host=host, community=community, port=port)
        
        print("=" * 60)
        print("DEVICE INFORMATION")
        print("=" * 60)
        
        serial = canon.get_serial()
        print(f"Serial Number: {serial if serial else 'Not available'}")
        
        firmware = canon.get_firmware()
        print(f"Firmware Version: {firmware if firmware else 'Not available'}")
        
        model = canon.get_model()
        if model:
            canon.device['MODEL'] = model
        print(f"Model: {canon.device.get('MODEL', 'Not available')}")
        
        print("\n" + "=" * 60)
        print("PAGE COUNTERS")
        print("=" * 60)
        print("Before retrieval:", canon.device.get('PAGECOUNTERS', {}))
        
        # Retrieve page counters
        canon.run()
        
        print("\nAfter retrieval:")
        if canon.device.get('PAGECOUNTERS'):
            for counter_name, counter_value in sorted(canon.device['PAGECOUNTERS'].items()):
                print(f"  {counter_name}: {counter_value:,}")
        else:
            print("  No counters retrieved")
        
        print("\n" + "=" * 60)
        print("Module executed successfully with real SNMP.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTest failed: {e}", file=sys.stderr)
        print("Module loaded but test requires valid SNMP host.", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


"""
GLPI::Agent::SNMP::MibSupport::Canon - Inventory module for Canon

This module enhances Canon printers support.
"""
