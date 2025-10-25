#!/usr/bin/env python3
"""
GLPI Agent PartNumber Tools - Python Implementation

This module provides a base class to handle PartNumber specific cases.
"""

import os
import glob
import importlib
import re
from typing import Optional, List, Any


__all__ = [
    'PartNumberFactory',
    'PartNumberBase'
]


class PartNumberBase:
    """
    Base class for PartNumber handlers.
    
    Subclasses should implement:
    - category() - return category constant
    - manufacturer() - return manufacturer constant  
    - mm_id() - return module manufacturer ID constant (optional)
    - priority() - return priority constant (lower = checked first)
    - match_re() - return regex pattern for matching partnumbers (optional)
    - init() - initialize object with regex match groups
    """
    
    @staticmethod
    def category() -> str:
        """Return category for this PartNumber handler."""
        return ""
    
    @staticmethod
    def manufacturer() -> str:
        """Return manufacturer for this PartNumber handler."""
        return ""
    
    @staticmethod
    def mm_id() -> str:
        """Return module manufacturer ID for this PartNumber handler."""
        return ""
    
    @staticmethod
    def priority() -> int:
        """Return priority (lower values checked first)."""
        return 50
    
    @staticmethod
    def match_re():
        """Return regex pattern for matching partnumbers."""
        return None
    
    def __init__(self, logger=None):
        """Initialize PartNumber instance."""
        self.logger = logger
        self._speed = None
        self._type = None
        self._revision = None
        self._partnumber = None
    
    def init(self, *matches):
        """Initialize with regex match groups (to be overridden by subclasses)."""
        pass
    
    def speed(self) -> Optional[Any]:
        """Get memory speed."""
        return self._speed
    
    def type(self) -> Optional[str]:
        """Get memory type."""
        return self._type
    
    def revision(self) -> Optional[str]:
        """Get revision part from partnumber."""
        return self._revision
    
    def get(self) -> Optional[str]:
        """Get the partnumber itself."""
        return self._partnumber


class PartNumberFactory:
    """
    Factory for creating PartNumber objects with dynamic subclass loading.
    """
    
    _subclasses: Optional[List] = None
    
    def __init__(self, logger=None):
        """
        Initialize PartNumber factory.
        
        Args:
            logger: Logger object
        """
        self.logger = logger
        
        if PartNumberFactory._subclasses is None:
            PartNumberFactory._subclasses = []
            self._load_subclasses()
    
    def _load_subclasses(self):
        """Load all PartNumber subclasses from the PartNumber directory."""
        # Get the directory containing this module
        module_dir = os.path.dirname(os.path.abspath(__file__))
        partnumber_dir = os.path.join(module_dir, 'PartNumber')
        
        if not os.path.isdir(partnumber_dir):
            if self.logger:
                self.logger.debug(f"PartNumber directory not found: {partnumber_dir}")
            return
        
        # Find all Python files in the PartNumber directory
        pattern = os.path.join(partnumber_dir, '*.py')
        priority_map = {}
        
        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)
            
            # Skip __init__.py
            if filename.startswith('__'):
                continue
            
            # Get module name without .py extension
            module_name = filename[:-3]
            
            try:
                # Import the module
                full_module_name = f'GLPI.Agent.Tools.PartNumber.{module_name}'
                module = importlib.import_module(full_module_name)
                
                # Find the PartNumber class in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    # Check if it's a class that inherits from PartNumberBase
                    if (isinstance(attr, type) and 
                        issubclass(attr, PartNumberBase) and 
                        attr != PartNumberBase):
                        
                        priority = attr.priority()
                        priority_map[attr] = priority
                        break
                        
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to load PartNumber::{module_name}")
                    self.logger.debug2(f"{full_module_name} require error: {e}")
                continue
        
        # Sort by priority (lower first), then by name
        PartNumberFactory._subclasses = sorted(
            priority_map.keys(),
            key=lambda x: (priority_map[x], x.__name__)
        )
    
    def match(self, partnumber: Optional[str] = None, 
             category: Optional[str] = None,
             manufacturer: Optional[str] = None,
             mm_id: Optional[str] = None) -> Optional[PartNumberBase]:
        """
        Match partnumber against available subclasses.
        
        Args:
            partnumber: Partnumber string to match
            category: Filter by category
            manufacturer: Filter by manufacturer
            mm_id: Filter by module manufacturer ID
            
        Returns:
            PartNumber object if match found, None otherwise
        """
        if partnumber is None:
            return None
        
        for subclass in PartNumberFactory._subclasses:
            # Filter by category
            if category and subclass.category() != category:
                continue
            
            # Filter by manufacturer (prefer mm_id if available)
            if mm_id and subclass.mm_id():
                if subclass.mm_id() != mm_id:
                    continue
            elif manufacturer:
                if subclass.manufacturer() != manufacturer:
                    continue
            
            # Try to match partnumber with regex
            matches = []
            match_regex = subclass.match_re()
            
            if match_regex:
                match = re.search(match_regex, partnumber)
                if not match:
                    continue
                matches = match.groups()
            else:
                # Only support no partnumber regexp if mm_id matched
                if not mm_id:
                    continue
            
            # Create instance and initialize
            instance = subclass(logger=self.logger)
            instance.init(*matches)
            
            # Only validate Partnumber object if it has a manufacturer
            if not instance.manufacturer():
                continue
            
            return instance
        
        return None


if __name__ == '__main__':
    print("GLPI Agent PartNumber Tools")
    print("Available classes:")
    for cls in __all__:
        print(f"  - {cls}")
    
    # Test factory
    print("\nTesting PartNumberFactory:")
    factory = PartNumberFactory()
    print(f"  Loaded {len(PartNumberFactory._subclasses)} subclasses")
