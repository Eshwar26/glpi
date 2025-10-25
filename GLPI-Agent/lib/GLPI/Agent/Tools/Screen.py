#!/usr/bin/env python3
"""
GLPI Agent Screen Tools - Python Implementation

This is an abstract base class for screen/monitor objects.
"""

import importlib
from typing import Optional, Dict, Any
import re

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools.Generic import get_edid_vendor
except ImportError:
    # Mock for standalone usage
    def get_edid_vendor(**params):
        return None


__all__ = [
    'Screen'
]


# EDID manufacturer to subclass mapping
EDID_MANUFACTURER_TO_SUBCLASS = {
    'ACR': 'Acer',
    'AIC': 'Neovo',
    'BNQ': 'BenQ',
    'ENC': 'Eizo',
    'GSM': 'Goldstar',
    'PHL': 'Philips',
    'SAM': 'Samsung'
}


class Screen:
    """
    Base class for screen/monitor objects.
    """
    
    def __init__(self, edid: Dict[str, Any], logger=None, datadir: Optional[str] = None):
        """
        Initialize screen object from EDID data.
        
        Args:
            edid: Dictionary containing parsed EDID data
            logger: Logger object
            datadir: Data directory for vendor lookup
        """
        self.logger = logger
        self.edid = edid
        self._serial = None
        self._caption = None
        self._manufacturer = None
        
        # Handle serial number
        # There are two different serial numbers in EDID:
        # - a mandatory 4 bytes numeric value
        # - an optional 13 bytes ASCII value
        # We use the ASCII value if present, the numeric value as a hex string
        serial_number2 = edid.get('serial_number2')
        if serial_number2 and serial_number2:
            self._serial = str(serial_number2[0]) if isinstance(serial_number2, (list, tuple)) else str(serial_number2)
            # Check if serial ends by 0x0A (linefeed) - problem found on Lenovo monitors
            lf_index = self._serial.find('\n')
            if lf_index >= 0:
                self._serial = self._serial[:lf_index]
        else:
            serial_number = edid.get('serial_number', 0)
            self._serial = f"{serial_number:08x}"
        
        # Setup manufacturer
        edid_vendor = get_edid_vendor(
            id=edid.get('manufacturer_name'),
            datadir=datadir
        )
        self.manufacturer(edid_vendor or edid.get('manufacturer_name'))
        
        # Try to overload with manufacturer-specific subclass
        self._overload_subclass()
    
    def _overload_subclass(self):
        """Overload class with manufacturer-specific subclass if available."""
        edid_name = self.edid.get('manufacturer_name')
        if not edid_name:
            return
        
        manufacturer_class = EDID_MANUFACTURER_TO_SUBCLASS.get(edid_name)
        if manufacturer_class:
            try:
                # Try to import the subclass module
                module_name = f'GLPI.Agent.Tools.Screen.{manufacturer_class}'
                module = importlib.import_module(module_name)
                
                # Get the class from the module
                cls = getattr(module, manufacturer_class, None)
                if cls:
                    # Change the instance's class to the subclass
                    self.__class__ = cls
            except (ImportError, AttributeError):
                # Subclass not available, continue with base class
                pass
    
    def eisa_id(self) -> Optional[str]:
        """Get EISA ID."""
        return self.edid.get('EISA_ID')
    
    def serial(self) -> Optional[str]:
        """Get serial number."""
        return self._serial
    
    def altserial(self) -> Optional[str]:
        """Get alternative serial number (to be overridden in subclasses)."""
        return None
    
    def week_year_manufacture(self) -> str:
        """
        Get week and year of manufacture.
        
        Returns:
            String in format "week/year" or just "year" if week is 255
        """
        week = self.edid.get('week', 0)
        year = self.edid.get('year', 0)
        
        # Skip week if set to 255 (see EDID specs)
        if week == 255:
            return str(year)
        else:
            return f"{week}/{year}"
    
    def caption(self) -> Optional[str]:
        """
        Get monitor caption/name.
        
        Returns:
            Monitor name or computed monitor text
        """
        if self._caption:
            return self._caption
        
        # Try monitor_name first
        self._caption = self.edid.get('monitor_name')
        
        # Fall back to monitor_text if available
        if not self._caption:
            monitor_text = self.edid.get('monitor_text')
            if monitor_text and isinstance(monitor_text, (list, tuple)):
                self._caption = ' '.join(monitor_text)
        
        if not self._caption:
            return None
        
        # Skip empty/whitespace-only captions
        if not self._caption.strip():
            return None
        
        # Clean-up: remove non-printable characters
        self._caption = re.sub(r'[^ -~].*$', '', self._caption)
        
        return self._caption if self._caption.strip() else None
    
    def manufacturer(self, manufacturer: Optional[str] = None) -> Optional[str]:
        """
        Get or set manufacturer name.
        
        Args:
            manufacturer: Manufacturer name to set (optional)
            
        Returns:
            Manufacturer name
        """
        if manufacturer is not None:
            self._manufacturer = manufacturer
        return self._manufacturer


if __name__ == '__main__':
    print("GLPI Agent Screen Tools")
    print("Available classes:")
    for cls in __all__:
        print(f"  - {cls}")
    
    # Test with sample EDID data
    print("\nTesting Screen class:")
    sample_edid = {
        'manufacturer_name': 'DEL',
        'serial_number': 12345,
        'week': 10,
        'year': 2020,
        'monitor_name': 'Dell U2415'
    }
    
    screen = Screen(sample_edid)
    print(f"  Serial: {screen.serial()}")
    print(f"  Caption: {screen.caption()}")
    print(f"  Week/Year: {screen.week_year_manufacture()}")
    print(f"  Manufacturer: {screen.manufacturer()}")
