#!/usr/bin/env python3
"""
GLPI Agent Screen Philips Module - Python Implementation

Philips screen-specific serial number handling.
Handles cases where monitor doesn't report serial2 in EDID while connected
through HDMI port. In that case, we use serial1 as an integer, not hex.
"""

from typing import Optional

try:
    from GLPI.Agent.Tools.Screen import Screen
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Screen import Screen


class Philips(Screen):
    """Philips screen handler with HDMI-specific serial handling."""
    
    def _has_serial_number2(self) -> bool:
        """
        Check if serial_number2 exists in EDID data.
        
        Returns:
            True if serial_number2 exists and is not empty
        """
        if not hasattr(self, 'edid') or not self.edid:
            return False
        
        serial_number2 = self.edid.get('serial_number2')
        return bool(serial_number2 and serial_number2)
    
    def serial(self) -> Optional[str]:
        """
        Get serial number, reverting to decimal format if no serial2.
        
        Returns:
            Serial number string or None
        """
        # Revert serial and altserial when no serial2 found
        if not self._has_serial_number2():
            return self._altserial()
        
        return getattr(self, '_serial', None)
    
    def altserial(self) -> Optional[str]:
        """
        Get alternative serial number.
        
        Returns:
            Alternative serial number or None
        """
        if hasattr(self, '_altserial_cached'):
            return self._altserial_cached
        
        # Revert serial and altserial when no serial2 found
        if self._has_serial_number2():
            self._altserial_cached = self._altserial()
        else:
            self._altserial_cached = getattr(self, '_serial', None)
        
        return self._altserial_cached
    
    def _altserial(self) -> Optional[str]:
        """
        Generate alternative serial as 6-digit decimal.
        
        Returns:
            Decimal serial or None
        """
        if not hasattr(self, 'edid') or not self.edid:
            return None
        
        serial1 = self.edid.get('serial_number')
        if serial1 is None:
            return None
        
        serial1_str = f"{serial1:06d}"
        
        # Don't report altserial if current serial still includes it
        current_serial = getattr(self, '_serial', '')
        if current_serial and serial1_str in current_serial:
            return None
        
        return serial1_str


if __name__ == '__main__':
    print("GLPI Agent Screen Philips Module")
