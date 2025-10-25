#!/usr/bin/env python3
"""
GLPI Agent Expiration Tools - Python Implementation

This module provides time-out related functions for operation expiration.
"""

import time
from typing import Optional


__all__ = [
    'set_expiration_time',
    'get_expiration_time'
]


# Module-level variable to store expiration time
_expiration_time: Optional[float] = None


def set_expiration_time(timeout: Optional[int] = None, 
                       expiration: Optional[float] = None) -> bool:
    """
    Set current expiration time.
    
    Args:
        timeout: Timeout in seconds from now
        expiration: Absolute expiration timestamp
        
    Returns:
        True if expiration was set, False otherwise
    """
    global _expiration_time
    
    if timeout is not None:
        _expiration_time = time.time() + timeout
        return True
    elif expiration is not None:
        _expiration_time = expiration
        return True
    else:
        _expiration_time = None
        return False


def get_expiration_time() -> float:
    """
    Get current expiration time.
    
    Returns:
        Expiration timestamp, or 0 if not set
    """
    return _expiration_time if _expiration_time is not None else 0.0


if __name__ == '__main__':
    print("GLPI Agent Expiration Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
    
    # Test functions
    print("\nTesting expiration functions:")
    print(f"Initial expiration: {get_expiration_time()}")
    
    set_expiration_time(timeout=10)
    print(f"After setting 10 second timeout: {get_expiration_time()}")
    print(f"Current time: {time.time()}")
    print(f"Time remaining: {get_expiration_time() - time.time():.2f} seconds")
