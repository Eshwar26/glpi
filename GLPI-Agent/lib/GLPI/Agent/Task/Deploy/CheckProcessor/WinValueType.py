"""
GLPI Agent Task Deploy CheckProcessor WinValueType Module
"""

import platform


class WinValueType:
    """Check if Windows registry value type matches expected type"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize Windows value type check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        self._on_success = f"registry value type matches for: {self.path}"
    
    def success(self) -> bool:
        """Check if registry value type matches (Windows only)"""
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
