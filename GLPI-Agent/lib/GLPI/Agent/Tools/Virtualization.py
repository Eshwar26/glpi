#!/usr/bin/env python3
"""
GLPI Agent Virtualization Tools - Python Implementation

This module provides virtualization-related constants and functions.
"""

import hashlib
from typing import Optional


# Virtualization status constants
STATUS_RUNNING = 'running'
STATUS_BLOCKED = 'blocked'
STATUS_IDLE = 'idle'
STATUS_PAUSED = 'paused'
STATUS_SHUTDOWN = 'shutdown'
STATUS_CRASHED = 'crashed'
STATUS_DYING = 'dying'
STATUS_OFF = 'off'


__all__ = [
    'STATUS_RUNNING',
    'STATUS_BLOCKED',
    'STATUS_IDLE',
    'STATUS_PAUSED',
    'STATUS_SHUTDOWN',
    'STATUS_CRASHED',
    'STATUS_DYING',
    'STATUS_OFF',
    'get_virtual_uuid'
]


def get_virtual_uuid(machine_id: Optional[str], name: Optional[str]) -> str:
    """
    Generate UUID for virtual machine.
    
    Args:
        machine_id: Machine identifier
        name: Virtual machine name
        
    Returns:
        SHA1 hash of machine_id + name, or empty string if parameters are invalid
    """
    if not machine_id or not name:
        return ''
    
    # Create SHA1 hash of machine_id concatenated with name
    combined = machine_id + name
    return hashlib.sha1(combined.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    print("GLPI Agent Virtualization Tools")
    print("Available constants:")
    print(f"  STATUS_RUNNING: {STATUS_RUNNING}")
    print(f"  STATUS_BLOCKED: {STATUS_BLOCKED}")
    print(f"  STATUS_IDLE: {STATUS_IDLE}")
    print(f"  STATUS_PAUSED: {STATUS_PAUSED}")
    print(f"  STATUS_SHUTDOWN: {STATUS_SHUTDOWN}")
    print(f"  STATUS_CRASHED: {STATUS_CRASHED}")
    print(f"  STATUS_DYING: {STATUS_DYING}")
    print(f"  STATUS_OFF: {STATUS_OFF}")
    
    print("\nTesting get_virtual_uuid:")
    uuid = get_virtual_uuid('machine-123', 'vm-test')
    print(f"  UUID: {uuid}")
