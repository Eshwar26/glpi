"""
GLPI Agent Task Deploy CheckProcessor Module

This module provides a base class for processing deployment checks in the GLPI Agent.
It supports dynamic loading of check-specific subclasses based on check types.
"""

import os
import re
from typing import Dict, Any, Optional


class CheckProcessor:
    """
    Base class for processing deployment checks.
    
    Supports various check types including file/directory operations,
    Windows registry checks, and disk space verification.
    """
    
    # Constants
    OK = "ok"
    
    # Supported sub-class mapping - must be declared here
    CHECK_TYPE_TO_MODULE = {
        "directoryExists": "DirectoryExists",
        "directoryMissing": "DirectoryMissing",
        "fileExists": "FileExists",
        "fileMissing": "FileMissing",
        "fileSizeEquals": "FileSizeEquals",
        "fileSizeGreater": "FileSizeGreater",
        "fileSizeLower": "FileSizeLower",
        "fileSHA512": "FileSHA512",
        "fileSHA512mismatch": "FileSHA512Mismatch",
        "freespaceGreater": "FreeSpaceGreater",
        "winkeyExists": "WinKeyExists",
        "winkeyMissing": "WinKeyMissing",
        "winkeyEquals": "WinKeyEquals",
        "winkeyNotEquals": "WinKeyNotEquals",
        "winvalueExists": "WinValueExists",
        "winvalueMissing": "WinValueMissing",
        "winvalueType": "WinValueType",
    }
    
    def __init__(self, check: Optional[Dict[str, Any]] = None, logger=None, **params):
        """
        Initialize the CheckProcessor.
        
        Args:
            check: Dictionary containing check parameters
            logger: Logger instance for output
            **params: Additional parameters
        """
        # Initialize with check dictionary or empty dict
        if check:
            self.__dict__.update(check)
        
        self.logger = logger
        
        # Set default values
        if not hasattr(self, 'message'):
            self.message = 'no message'
        if not hasattr(self, 'status'):
            self.status = self.OK
        if not hasattr(self, 'return'):
            self.return_value = "ko"
        else:
            self.return_value = getattr(self, 'return')
        if not hasattr(self, 'type'):
            self.type = "n/a"
        
        # Expand environment variables from the path
        if hasattr(self, 'path') and self.path:
            # Unix-style: $VAR
            self.path = re.sub(r'\$(\w+)', lambda m: os.environ.get(m.group(1), ''), self.path)
            # Windows-style: %VAR%
            self.path = re.sub(r'%(\w+)%', lambda m: os.environ.get(m.group(1), ''), self.path)
        else:
            self.path = "~~ no path given ~~"
        
        # Dynamic subclass loading
        if self.type in self.CHECK_TYPE_TO_MODULE:
            module_name = self.CHECK_TYPE_TO_MODULE[self.type]
            try:
                # Attempt to dynamically load the appropriate subclass
                # In a real implementation, you would import the actual module
                # For example: from .directory_exists import DirectoryExists
                # This is a placeholder for the dynamic loading mechanism
                self._load_subclass(module_name)
            except Exception as e:
                self.error(f"Can't use {module_name} module: load failure ({e})")
    
    def _load_subclass(self, module_name: str):
        """
        Load and apply the appropriate subclass.
        
        Args:
            module_name: Name of the module to load
            
        Note:
            In a complete implementation, this would dynamically import
            and rebind the instance to the appropriate subclass.
        """
        # Placeholder for dynamic module loading
        # In Python, you would typically use importlib:
        # module = importlib.import_module(f'.{module_name.lower()}', package=__package__)
        # self.__class__ = getattr(module, module_name)
        pass
    
    def debug2(self, message: str):
        """Log a level-2 debug message."""
        if self.logger:
            self.logger.debug2(message)
    
    def debug(self, message: str):
        """Log a debug message."""
        if self.logger:
            self.logger.debug(message)
    
    def info(self, message: str):
        """Log an info message."""
        if self.logger:
            self.logger.info(message)
    
    def error(self, message: str):
        """Log an error message."""
        if self.logger:
            self.logger.error(message)
    
    def on_failure(self, message: str):
        """
        Set the failure message.
        
        Args:
            message: Message to display on check failure
        """
        self._on_failure = message
    
    def on_success(self, message: str):
        """
        Set the success message.
        
        Args:
            message: Message to display on check success
        """
        self._on_success = message
    
    def get_message(self) -> str:
        """
        Get the current message.
        
        Returns:
            The current message string
        """
        return self.message
    
    def is_type(self, check_type: Optional[str] = None) -> bool:
        """
        Check if the return type matches the given type.
        
        Args:
            check_type: Type to check against. If None, returns the return value.
            
        Returns:
            True if types match, False otherwise. If check_type is None,
            returns the return_value.
        """
        if check_type:
            return self.return_value == check_type
        return self.return_value
    
    def name(self) -> str:
        """
        Get the name of the check.
        
        Returns:
            The check name, type, or 'unsupported'
        """
        return getattr(self, 'name', None) or self.type or 'unsupported'
    
    def process(self, **params) -> str:
        """
        Process the check and return status.
        
        Args:
            **params: Additional parameters for processing
            
        Returns:
            The status string (OK or the return value)
        """
        self.prepare()
        
        if self.success():
            message = getattr(self, '_on_success', None) or 'unknown reason'
            if hasattr(self, '_on_success'):
                self.debug(f"check success: {message}")
        else:
            message = getattr(self, '_on_failure', None) or 'unknown reason'
            if hasattr(self, '_on_failure'):
                self.debug(f"check failure: {message}")
            self.status = self.return_value
        
        self.message = message
        
        return self.status
    
    # Methods to be overridden in subclasses
    
    def prepare(self):
        """
        Prepare the check for execution.
        
        This method should call on_failure & on_success methods.
        Override this in subclasses to implement specific check logic.
        """
        self.message = f"Not implemented '{self.type}' check processor"
    
    def success(self) -> bool:
        """
        Determine if the check was successful.
        
        This method should return True when the check is a success, False otherwise.
        Override this in subclasses to implement specific success conditions.
        
        Returns:
            True if check succeeded, False otherwise
        """
        self.info(f"Unsupported check: {self.message}")
        return True


# Example usage
if __name__ == "__main__":
    # Create a simple logger mock
    class SimpleLogger:
        def debug2(self, msg):
            print(f"[DEBUG2] {msg}")
        
        def debug(self, msg):
            print(f"[DEBUG] {msg}")
        
        def info(self, msg):
            print(f"[INFO] {msg}")
        
        def error(self, msg):
            print(f"[ERROR] {msg}")
    
    # Example check
    check_data = {
        'type': 'fileExists',
        'path': '$HOME/test.txt',
        'return': 'error'
    }
    
    logger = SimpleLogger()
    processor = CheckProcessor(check=check_data, logger=logger)
    
    print(f"Check name: {processor.name()}")
    print(f"Check path: {processor.path}")
    status = processor.process()
    print(f"Status: {status}")
    print(f"Message: {processor.get_message()}")