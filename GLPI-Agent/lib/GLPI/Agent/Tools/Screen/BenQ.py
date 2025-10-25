#!/usr/bin/env python3
"""
GLPI Agent Screen BenQ Module - Python Implementation

BenQ screen-specific serial number handling.
"""

import struct
from typing import Optional

try:
    from GLPI.Agent.Tools.Screen import Screen
    from GLPI.Agent.Tools import empty
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Screen import Screen
    def empty(val):
        return not val


class BenQ(Screen):
    """BenQ screen handler with prefix-based serial numbers."""
    
    def serial(self) -> Optional[str]:
        """
        Get serial number with optional prefix.
        
        Returns:
            Serial number string or None
        """
        prefix = None
        
        if hasattr(self, 'edid') and self.edid and self.edid.get('serial_number2'):
            serial_num = self.edid.get('serial_number')
            if serial_num:
                try:
                    # Pack as little-endian unsigned long, then unpack as zero-terminated string
                    packed = struct.pack('<L', serial_num)
                    prefix = packed.decode('ascii', errors='ignore').rstrip('\x00')
                    # Validate prefix is all uppercase letters
                    if not prefix.isupper() or not prefix.isalpha():
                        prefix = None
                except (struct.error, ValueError, UnicodeDecodeError):
                    prefix = None
        
        serial_val = self._serial if hasattr(self, '_serial') else None
        fixed_serial = f"{prefix}{serial_val}" if prefix and serial_val else serial_val
        self._fixed_serial = fixed_serial
        
        return fixed_serial
    
    def altserial(self) -> Optional[str]:
        """
        Get alternative serial number.
        
        Returns:
            Alternative serial number or None
        """
        fixed = getattr(self, '_fixed_serial', None)
        orig = getattr(self, '_serial', None)
        
        # Return None if fixed serial is empty or same as original
        if empty(fixed) or (fixed == orig):
            return None
        
        return orig


if __name__ == '__main__':
    print("GLPI Agent Screen BenQ Module")
