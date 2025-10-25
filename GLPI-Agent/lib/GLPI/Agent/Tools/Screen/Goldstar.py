#!/usr/bin/env python3
"""
GLPI Agent Screen Goldstar Module - Python Implementation

Goldstar/LG screen-specific serial number handling with custom alphabet encoding.
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
EISA_ID_MATCH = re.compile(r'4b21$', re.I)


class Goldstar(Screen):
    """Goldstar/LG screen handler with special encoding."""
    
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
        
        return getattr(self, '_serial', None)
    
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
            self._altserial_cached = getattr(self, '_serial', None)
        else:
            self._altserial_cached = self._altserial()
        
        return self._altserial_cached
    
    def _altserial(self) -> Optional[str]:
        """
        Generate alternative serial using custom alphabet encoding.
        
        Returns:
            Encoded serial or None
        """
        if not hasattr(self, 'edid') or not self.edid:
            return None
        
        serial1 = self.edid.get('serial_number')
        if not serial1:
            return None
        
        # Split serial in two parts
        serial_str = str(serial1)
        match = re.search(r'(\d+)(\d{3})$', serial_str)
        if not match:
            return None
        
        high_str = match.group(1)
        low = match.group(2)
        
        try:
            high = int(high_str)
        except ValueError:
            return None
        
        # Translate the first part using a custom alphabet
        alphabet = list("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ")
        base = len(alphabet)
        
        if high // base >= len(alphabet):
            return None
        
        return f"{alphabet[high // base]}{alphabet[high % base]}{low}"


if __name__ == '__main__':
    print("GLPI Agent Screen Goldstar Module")
