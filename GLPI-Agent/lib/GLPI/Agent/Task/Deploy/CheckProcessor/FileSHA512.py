"""
GLPI Agent Task Deploy CheckProcessor FileSHA512 Module
"""

import os
import hashlib


class FileSHA512:
    """Check if file SHA512 hash matches expected value"""
    
    def __init__(self, path, value=None, logger=None):
        """Initialize file SHA512 check"""
        self.path = path
        self.value = value
        self.logger = logger
        self._on_success = None
        self._on_failure = None
    
    def prepare(self) -> None:
        """Prepare check messages"""
        self._on_success = f"got expected sha512 file hash for {self.path}"
    
    def success(self) -> bool:
        """Check if file SHA512 matches"""
        self._on_failure = f"{self.path} file is missing"
        if not os.path.isfile(self.path):
            return False
        
        self._on_failure = "no value provided to check file size against"
        expected = self.value
        if not expected:
            return False
        
        self._on_failure = "sha512 hash computing not supported by agent"
        sha512 = ""
        
        try:
            with open(self.path, 'rb') as f:
                sha512 = hashlib.sha512(f.read()).hexdigest()
        except Exception as e:
            self._on_failure = f"{self.path} file sha512 hash computing failed, {e}"
            return False
        
        if not sha512:
            return False
        
        self._on_failure = f"{self.path} has wrong sha512 file hash, found {sha512}"
        return sha512 == expected.lower()
    
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
