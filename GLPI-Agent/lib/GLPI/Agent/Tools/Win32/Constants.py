#!/usr/bin/env python3
"""
GLPI Agent Win32 Constants - Python Implementation

Windows-specific software category constants.
"""

__all__ = [
    'CATEGORY_SYSTEM_COMPONENT',
    'CATEGORY_APPLICATION',
    'CATEGORY_UPDATE',
    'CATEGORY_SECURITY_UPDATE',
    'CATEGORY_HOTFIX'
]

# Software category constants
CATEGORY_SYSTEM_COMPONENT = 'system_component'
CATEGORY_APPLICATION = 'application'
CATEGORY_UPDATE = 'update'
CATEGORY_SECURITY_UPDATE = 'security_update'
CATEGORY_HOTFIX = 'hotfix'


if __name__ == '__main__':
    print("GLPI Agent Win32 Constants Module")
    print(f"Categories: {', '.join([CATEGORY_SYSTEM_COMPONENT, CATEGORY_APPLICATION, CATEGORY_UPDATE, CATEGORY_SECURITY_UPDATE, CATEGORY_HOTFIX])}")
