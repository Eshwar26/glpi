"""
GLPI Agent ToolBox Results Fields Module

Base class for result field definitions and processing.
"""

from typing import Dict, Any, List, Optional, Callable
import ipaddress


class Fields:
    """
    Base class for defining fields in result sources.
    
    Provides field definitions, sections, and processing logic.
    """

    def __init__(self, **params):
        """
        Initialize fields handler.
        
        Args:
            **params: Parameters including results object
        """
        self.results = params.get('results')
        self.logger = None
        
        if self.results and hasattr(self.results, 'logger'):
            self.logger = self.results.logger
        
        self._name = self.__class__.__name__

    def name(self) -> str:
        """
        Get the source name.
        
        Returns:
            Source name
        """
        return self._name

    def order(self) -> int:
        """
        Get the processing order.
        
        Lower numbers are processed first.
        
        Returns:
            Order number
        """
        return 0

    def any(self) -> bool:
        """
        Check if this source applies to any file type.
        
        Returns:
            True if applicable to any file
        """
        return False

    def sections(self) -> List[Dict[str, Any]]:
        """
        Get field sections for UI organization.
        
        Returns:
            List of section definitions
        """
        return []

    def fields(self) -> List[Dict[str, Any]]:
        """
        Get field definitions.
        
        Returns:
            List of field definitions
        """
        return []

    def analyze(self, name: str, data: Any, file: str) -> Optional[Dict[str, Any]]:
        """
        Analyze device data and extract fields.
        
        Args:
            name: Device name
            data: Device data
            file: File path
            
        Returns:
            Dictionary of extracted fields or None
        """
        return None

    def sortable_by_ip(self, ip: str) -> List[int]:
        """
        Convert IP address to sortable format.
        
        Args:
            ip: IP address string
            
        Returns:
            List of integers representing IP octets
        """
        try:
            # Try to parse as IPv4
            addr = ipaddress.IPv4Address(ip)
            return list(addr.packed)
        except:
            try:
                # Try to parse as IPv6
                addr = ipaddress.IPv6Address(ip)
                return list(addr.packed)
            except:
                # Return IP as-is if not parseable
                return [ord(c) for c in ip[:16].ljust(16, '\0')]

    def log_prefix(self) -> str:
        """
        Get log prefix for this source.
        
        Returns:
            Log prefix string
        """
        return f"[toolbox plugin, results, {self.name()}] "

    def debug(self, message: str):
        """
        Log debug message.
        
        Args:
            message: Debug message
        """
        if self.logger and hasattr(self.logger, 'debug'):
            self.logger.debug(self.log_prefix() + message)

    def info(self, message: str):
        """
        Log info message.
        
        Args:
            message: Info message
        """
        if self.logger and hasattr(self.logger, 'info'):
            self.logger.info(self.log_prefix() + message)

    def error(self, message: str):
        """
        Log error message.
        
        Args:
            message: Error message
        """
        if self.logger and hasattr(self.logger, 'error'):
            self.logger.error(self.log_prefix() + message)

