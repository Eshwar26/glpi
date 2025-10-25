#!/usr/bin/env python3
"""
GLPI Agent PartNumber Patriot Module - Python Implementation

Patriot Memory part number handler.
"""

import re
from typing import Optional

try:
    from GLPI.Agent.Tools.PartNumber import PartNumber
except ImportError:
    import sys
    sys.path.insert(0, '../../../')
    from PartNumber import PartNumber


class Patriot(PartNumber):
    """Patriot Memory part number handler."""
    
    MATCH_RE = None  # No specific pattern matching
    CATEGORY = "memory"
    MANUFACTURER = "Patriot Memory"
    MM_ID = "Bank 6, Hex 0x02"


if __name__ == '__main__':
    print("GLPI Agent PartNumber Patriot Module")
