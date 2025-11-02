#!/usr/bin/env python3
"""Win32::TieRegistry fake module for non-Windows platforms"""

# Constants
REG_SZ = 0x1
REG_DWORD = 0x4

# Global registry object
Registry = {}


class TieRegistry(dict):
    """Mock Win32::TieRegistry for testing on non-Windows platforms"""
    
    REG_SZ = REG_SZ
    REG_DWORD = REG_DWORD
    
    def GetValue(self, value):
        """
        Get registry value.
        
        Args:
            value: Value name or subkey name
            
        Returns:
            For subkeys: None
            For values: Tuple of (value, type) or just value depending on context
        """
        # Subkey case - check if it exists as a key ending with /
        if value and (value + '/') in self:
            return None
        
        # Value case - check if it exists with / prefix
        value_key = '/' + value if value else '/'
        if value_key in self:
            val = self[value_key]
            # Check if it's a DWORD (starts with 0x)
            reg_type = REG_DWORD if isinstance(val, str) and val.startswith('0x') else REG_SZ
            return (val, reg_type) if hasattr(self, '_wantarray') else val
        
        return None
    
    def SubKeyNames(self, key=None):
        """
        Get subkey names.
        
        Args:
            key: Optional key name (unused in mock)
            
        Returns:
            List of subkey names (keys ending with /)
        """
        return [k.rstrip('/') for k in self.keys() if k.endswith('/')]
    
    def Information(self):
        """
        Get registry key information.
        
        Returns:
            Dictionary with CntValues (count of values)
        """
        # Count values (keys starting with /)
        cnt_values = len([k for k in self.keys() if k.startswith('/')])
        return {'CntValues': cnt_values}
    
    def Handle(self):
        """Get handle (no-op in mock)"""
        return None
    
    def Open(self, subkey):
        """
        Open a subkey.
        
        Args:
            subkey: Subkey name
            
        Returns:
            Registry object for the subkey
        """
        subkey_path = subkey + '/' if not subkey.endswith('/') else subkey
        if subkey_path not in self:
            self[subkey_path] = TieRegistry()
        return self[subkey_path]


# Module-level functions for compatibility
def KEY_READ():
    """Mock KEY_READ constant"""
    return None


# For import compatibility
__all__ = ['Registry', 'REG_SZ', 'REG_DWORD', 'KEY_READ', 'TieRegistry']
