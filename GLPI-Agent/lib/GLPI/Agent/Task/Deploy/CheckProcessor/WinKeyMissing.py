"""
GLPI Agent Task Deploy CheckProcessor WinKeyMissing Module
"""

import platform
import re


class WinKeyMissing:
    """Check if Windows registry key is missing"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize Windows key missing check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        self.path = re.sub(r'\\', '/', self.path)
        self.path = re.sub(r'/+$', '', self.path)
        self._on_success = f"registry key not found: {self.path}/"
    
    def success(self) -> bool:
        """Check if registry key is missing (Windows only)"""
        self._on_failure = "check only available on windows"
        if platform.system() != 'Windows':
            return False
        
        # Placeholder - would check Windows registry
        return False
    
    def on_failure(self, msg: str = None) -> str:
        if msg:
            self._on_failure = msg
        return self._on_failure or ""
    
    def on_success(self, msg: str = None) -> str:
        if msg:
            self._on_success = msg
        return self._on_success or ""
