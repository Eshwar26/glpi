"""
GLPI Agent Task Deploy CheckProcessor WinKeyExists Module
"""

import platform
import re


class WinKeyExists:
    """Check if Windows registry key exists"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize Windows key exists check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        # Normalize path
        self.path = re.sub(r'\\', '/', self.path)
        self.path = re.sub(r'/+$', '', self.path)
        
        self._on_success = f"registry key found: {self.path}/"
    
    def success(self) -> bool:
        """Check if registry key exists (Windows only)"""
        self._on_failure = "check only available on windows"
        if platform.system() != 'Windows':
            return False
        
        try:
            # Would import Windows registry tools
            # from GLPI.Agent.Tools.Win32 import get_registry_key
            pass
        except Exception as e:
            self._on_failure = f"failed to load Win32 tools: {e}"
            return False
        
        # Parse parent and key
        match = re.match(r'^(.*)/([^/]*)$', self.path)
        self._on_failure = f"registry path not supported: {self.path}"
        if not match:
            return False
        
        parent, key = match.groups()
        
        self._on_failure = f"missing parent registry key: {parent}/"
        
        # In real implementation:
        # parent_key = get_registry_key(path=parent)
        # if not parent_key:
        #     return False
        #
        # # Test if path could be seen as a value path
        # if f'/{key}' in parent_key:
        #     self._on_failure = f"missing registry key, but can be seen as a value: {self.path}"
        # else:
        #     self._on_failure = f"missing registry key: {self.path}/"
        #
        # return f'{key}/' in parent_key
        
        # Placeholder
        return False
    
    def on_failure(self, msg: str = None) -> str:
        """Get or set failure message"""
        if msg:
            self._on_failure = msg
        return self._on_failure or ""
    
    def on_success(self, msg: str = None) -> str:
        """Get or set success message"""
        if msg:
            self._on_success = msg
        return self._on_success or ""
