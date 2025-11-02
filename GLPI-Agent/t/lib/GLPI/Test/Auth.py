#!/usr/bin/env python3
"""Test Authentication Module - Simple authentication for testing"""

import base64
from typing import Optional


class Auth:
    """Simple authentication adapter for testing"""
    
    def __init__(self, user: str, password: str):
        """
        Initialize authentication adapter.
        
        Args:
            user: Username for authentication
            password: Password for authentication
        """
        self.user = user
        self.password = password
    
    def check(self, user: str, password: str) -> bool:
        """
        Check if credentials match.
        
        Args:
            user: Username to check
            password: Password to check
            
        Returns:
            True if credentials match, False otherwise
        """
        return user == self.user and password == self.password
    
    def check_auth_header(self, auth_header: Optional[str]) -> bool:
        """
        Check Authorization header.
        
        Args:
            auth_header: Authorization header value (e.g., "Basic base64string")
            
        Returns:
            True if authenticated, False otherwise
        """
        if not auth_header or not auth_header.startswith('Basic '):
            return False
        
        try:
            # Decode base64 credentials
            encoded = auth_header[6:]  # Remove "Basic " prefix
            decoded = base64.b64decode(encoded).decode('utf-8')
            user, password = decoded.split(':', 1)
            return self.check(user, password)
        except (ValueError, UnicodeDecodeError):
            return False
