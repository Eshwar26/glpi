#!/usr/bin/env python3
"""
GLPI Agent UUID Tools - Python Implementation

This module provides UUID generation and validation utilities.
"""

import uuid
import re
from typing import Optional


__all__ = [
    'create_uuid',
    'create_uuid_from_name',
    'is_uuid_string',
    'uuid_to_string'
]


# UUID string validation pattern (imported from UUID::Tiny)
IS_UUID_STRING = re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$', re.IGNORECASE)


def create_uuid() -> uuid.UUID:
    """
    Create a new random UUID (UUID4).
    
    Returns:
        UUID object
    """
    return uuid.uuid4()


def create_uuid_from_name(name: str) -> uuid.UUID:
    """
    Create a UUID from a name using UUID5 (SHA-1 hash).
    
    Args:
        name: Name string to generate UUID from
        
    Returns:
        UUID object
    """
    # Use DNS namespace as in the original Perl code
    return uuid.uuid5(uuid.NAMESPACE_DNS, name)


def uuid_to_string(uuid_obj: Optional[uuid.UUID]) -> str:
    """
    Convert UUID object to lowercase string representation.
    
    Args:
        uuid_obj: UUID object or UUID string
        
    Returns:
        Lowercase UUID string, or empty string if None
    """
    if uuid_obj is None:
        return ''
    
    # Handle both UUID objects and strings
    if isinstance(uuid_obj, uuid.UUID):
        return str(uuid_obj).lower()
    elif isinstance(uuid_obj, str):
        return uuid_obj.lower()
    elif isinstance(uuid_obj, bytes):
        # Convert bytes to UUID object first
        try:
            return str(uuid.UUID(bytes=uuid_obj)).lower()
        except Exception:
            return ''
    
    return ''


def is_uuid_string(uuid_str: Optional[str]) -> bool:
    """
    Check if a string is a valid UUID format.
    
    Args:
        uuid_str: String to validate
        
    Returns:
        True if string is a valid UUID format
    """
    if uuid_str is None:
        return False
    
    return IS_UUID_STRING.match(uuid_str) is not None


if __name__ == '__main__':
    print("GLPI Agent UUID Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
    
    # Test functions
    print("\nTesting UUID functions:")
    
    # Create random UUID
    random_uuid = create_uuid()
    print(f"Random UUID: {uuid_to_string(random_uuid)}")
    
    # Create UUID from name
    name_uuid = create_uuid_from_name("example.com")
    print(f"UUID from name 'example.com': {uuid_to_string(name_uuid)}")
    
    # Validate UUID strings
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    invalid_uuid = "not-a-uuid"
    print(f"Is '{valid_uuid}' valid UUID? {is_uuid_string(valid_uuid)}")
    print(f"Is '{invalid_uuid}' valid UUID? {is_uuid_string(invalid_uuid)}")
