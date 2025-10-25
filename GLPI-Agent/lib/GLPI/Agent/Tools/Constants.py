#!/usr/bin/env python3
"""
GLPI Agent Constants - Python Implementation

This module provides constants for the GLPI Agent.
"""

# Status constants
STATUS_ON = 'on'
STATUS_OFF = 'off'

__all__ = [
    'STATUS_OFF',
    'STATUS_ON'
]


if __name__ == '__main__':
    print("GLPI Agent Constants")
    print(f"STATUS_ON: {STATUS_ON}")
    print(f"STATUS_OFF: {STATUS_OFF}")
