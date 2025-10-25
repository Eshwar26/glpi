#!/usr/bin/env python3
"""
GLPI Agent Screen Acer Module - Python Implementation

Acer screen-specific serial number handling.
"""

import re
from typing import Optional

try:
    from GLPI.Agent.Tools.Screen import Screen
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Screen import Screen


# Well-known eisa_id for which we need to revert serial and altserial
# List of model IDs that require special handling
_EISA_ID_MODELS = [
    '0018', '0019', '001a', '0020', '0024', '0026', '0031', '004b', '004c',
    '0069', '0070', '0076', '00a3', '00a8', '00c7', '00d2', '00db', '00f7',
    '0133', '0239', '02cc', '02d4', '0319', '0320', '032d', '032e', '0330',
    '0331', '0335', '0337', '0338', '0353', '0363', '03de', '0424', '042e',
    '0468', '046f', '047b', '0480', '0503', '0512', '0523', '056b', '057d',
    '057f', '0618', '0771', '0772', '0783', '033a', '1228', '1701', '1716',
    '2309', '2311', '2608', '2708', '5401', '56ad', '7883', 'ad46', 'ad49',
    'ad51', 'ad72', 'ad73', 'ad80', 'adaf'
]

EISA_ID_MATCH = re.compile('|'.join(_EISA_ID_MODELS) + '$', re.I)


class Acer(Screen):
    """Acer screen handler with special serial number processing."""
    
    def serial(self) -> Optional[str]:
        """
        Get serial number, possibly reverted based on EISA ID.
        
        Returns:
            Serial number string or None
        """
        # Revert serial and altserial when eisa_id matches
        eisa = self.eisa_id()
        if eisa and EISA_ID_MATCH.search(eisa):
            return self._altserial()
        
        return self._serial
    
    def altserial(self) -> Optional[str]:
        """
        Get alternative serial number.
        
        Returns:
            Alternative serial number or None
        """
        if hasattr(self, '_altserial_cached'):
            return self._altserial_cached
        
        # Revert serial and altserial when eisa_id matches
        eisa = self.eisa_id()
        if eisa and EISA_ID_MATCH.search(eisa):
            self._altserial_cached = self._serial
        else:
            self._altserial_cached = self._altserial()
        
        return self._altserial_cached
    
    def _altserial(self) -> Optional[str]:
        """
        Generate alternative serial from EDID data.
        
        Returns:
            Generated serial or None
        """
        if not hasattr(self, 'edid') or not self.edid:
            return None
        
        serial1 = self.edid.get('serial_number')
        if not serial1:
            return None
        
        serial_number2 = self.edid.get('serial_number2')
        if not serial_number2 or not serial_number2:
            return None
        
        serial2 = serial_number2[0] if isinstance(serial_number2, list) else serial_number2
        if not serial2 or len(serial2) < 12:
            return None
        
        # Split serial2
        part1 = serial2[0:8]
        part2 = serial2[8:12]
        
        # Assemble serial1 with serial2 parts
        return f"{part1}{serial1:08x}{part2}"


if __name__ == '__main__':
    print("GLPI Agent Screen Acer Module")
