#!/usr/bin/env python3
"""InstallerVersion - Support for installer version from sources for testing"""

import sys
from pathlib import Path

# Add lib paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

try:
    from GLPI.Agent.version import VERSION
except ImportError:
    # Fallback if module doesn't exist
    VERSION = "unknown"

DISTRO = "linux"


def get_version():
    """Get the agent version"""
    return VERSION

