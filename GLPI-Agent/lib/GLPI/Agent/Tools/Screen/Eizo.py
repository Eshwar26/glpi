#!/usr/bin/env python3
"""
GLPI Agent Screen Eizo Module - Python Implementation

Eizo screen-specific serial number handling.
"""

from typing import Optional

try:
    from GLPI.Agent.Tools.Screen import Screen
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Screen import Screen


class Eizo(Screen):
    """Eizo screen handler with conditional serial number usage."""
    
    def serial(self) -> Optional[str]:
        """
        Get serial number, preferring numeric serial if no serial_number2.
        
        Returns:
            Serial number string or None
        """
        # Don't use hex encoded serial if no serial_number2 is defined
        if not hasattr(self, 'edid') or not self.edid:
            return getattr(self, '_serial', None)
        
        serial_number2 = self.edid.get('serial_number2')
        if not serial_number2 or not serial_number2:
            # Use numeric serial number instead of hex encoded
            return self.edid.get('serial_number')
        
        # Use the regular hex-encoded serial
        return getattr(self, '_serial', None)


if __name__ == '__main__':
    print("GLPI Agent Screen Eizo Module")
