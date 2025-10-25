#!/usr/bin/env python3
"""
GLPI Agent Screen Samsung Module - Python Implementation

Samsung screen-specific serial number handling with multiple formats.
"""

import re
from typing import Optional

try:
    from GLPI.Agent.Tools.Screen import Screen
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Screen import Screen


# Well-known eisa_id patterns for different serial formats
EISA_ID_MATCH = re.compile(
    r'0572|0694|06b9|0833|0835|0978|09c6|09c7|0b66|0bc9|0c7b|0ca3|0ca5|0d1a|0e0f|0e1e',
    re.I
)

# For this model, prefix is in reverse order
EISA_ID_MATCH_2 = re.compile(r'0e5a$', re.I)

# For this model, the serial should be decimal, not hexadecimal
EISA_ID_MATCH_3 = re.compile(r'0c18$', re.I)


class Samsung(Screen):
    """Samsung screen handler with multiple serial formats."""
    
    def serial(self) -> Optional[str]:
        """
        Get serial number, format depends on EISA ID.
        
        Returns:
            Serial number string or None
        """
        eisa = self.eisa_id()
        if not eisa:
            return getattr(self, '_serial', None)
        
        # Revert serial and altserial when eisa_id matches
        if EISA_ID_MATCH.search(eisa):
            return self._altserial()
        
        if EISA_ID_MATCH_2.search(eisa):
            return self._altserial_2()
        
        if EISA_ID_MATCH_3.search(eisa):
            return self._altserial_3()
        
        return getattr(self, '_serial', None)
    
    def altserial(self) -> Optional[str]:
        """
        Get alternative serial number.
        
        Returns:
            Alternative serial number or None
        """
        if hasattr(self, '_altserial_cached'):
            return self._altserial_cached
        
        eisa = self.eisa_id()
        if not eisa:
            self._altserial_cached = self._altserial()
            return self._altserial_cached
        
        # Revert serial and altserial when eisa_id matches
        if EISA_ID_MATCH.search(eisa) or EISA_ID_MATCH_2.search(eisa):
            self._altserial_cached = getattr(self, '_serial', None)
        else:
            self._altserial_cached = self._altserial()
        
        return self._altserial_cached
    
    def _altserial(self) -> Optional[str]:
        """
        Generate alternative serial (standard format).
        
        Returns:
            Encoded serial or empty string
        """
        if not hasattr(self, 'edid') or not self.edid:
            return ''
        
        serial1 = self.edid.get('serial_number')
        if serial1 is None:
            return ''
        
        serial_number2 = self.edid.get('serial_number2')
        if not serial_number2 or not serial_number2:
            return ''
        
        serial2 = serial_number2[0] if isinstance(serial_number2, list) else serial_number2
        
        # Convert serial1 to 4 bytes
        try:
            return (
                chr((serial1 >> 24) % 256) +
                chr((serial1 >> 16) % 256) +
                chr((serial1 >> 8) % 256) +
                chr(serial1 % 256) +
                serial2
            )
        except (ValueError, TypeError):
            return ''
    
    def _altserial_2(self) -> Optional[str]:
        """
        Generate alternative serial (reverse byte order format).
        
        Returns:
            Encoded serial or empty string
        """
        if not hasattr(self, 'edid') or not self.edid:
            return ''
        
        serial1 = self.edid.get('serial_number')
        if serial1 is None:
            return ''
        
        serial_number2 = self.edid.get('serial_number2')
        if not serial_number2 or not serial_number2:
            return ''
        
        serial2 = serial_number2[0] if isinstance(serial_number2, list) else serial_number2
        
        # Convert serial1 to 4 bytes in reverse order
        try:
            return (
                chr(serial1 % 256) +
                chr((serial1 >> 8) % 256) +
                chr((serial1 >> 16) % 256) +
                chr((serial1 >> 24) % 256) +
                serial2
            )
        except (ValueError, TypeError):
            return ''
    
    def _altserial_3(self) -> Optional[int]:
        """
        Generate alternative serial (decimal format).
        
        Returns:
            Decimal serial number or None
        """
        if not hasattr(self, 'edid') or not self.edid:
            return None
        
        return self.edid.get('serial_number')


if __name__ == '__main__':
    print("GLPI Agent Screen Samsung Module")
