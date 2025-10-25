#!/usr/bin/env python3
"""
GLPI Agent Screen Neovo Module - Python Implementation

AG Neovo screen-specific handling.
"""

from typing import Optional

try:
    from GLPI.Agent.Tools.Screen import Screen
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from Screen import Screen


class Neovo(Screen):
    """AG Neovo screen handler."""
    
    def manufacturer(self) -> str:
        """
        Get manufacturer name.
        
        Returns:
            Manufacturer name
        """
        return "AG Neovo"


if __name__ == '__main__':
    print("GLPI Agent Screen Neovo Module")
