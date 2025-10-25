"""
GLPI Agent ToolBox Results Archive Module

Base class for archive format handlers.
"""

from typing import Dict, Any, Optional


class Archive:
    """
    Base class for archive format handlers.
    
    Subclasses implement specific archive formats like
    ZIP, TAR, 7z, etc.
    """

    def __init__(self, **params):
        """
        Initialize archive handler.
        
        Args:
            **params: Parameters including results object
        """
        # Get class name
        class_name = self.__class__.__name__
        
        # We are just a base class without fields
        if class_name == 'Archive':
            return None
        
        self.logger = None
        results = params.get('results')
        if results and hasattr(results, 'logger'):
            self.logger = results.logger
        
        self.results = results
        self._name = class_name
        self._order = 0
        self.archive = True
        self._filename: Optional[str] = None
        self._type: Optional[str] = None

    def name(self) -> str:
        """
        Get archive handler name.
        
        Returns:
            Handler name
        """
        return self._name

    def order(self) -> int:
        """
        Get processing order.
        
        Returns:
            Order number (default: 0)
        """
        return self._order

    def format(self) -> str:
        """
        Get archive format string.
        
        Override in subclasses.
        
        Returns:
            Format string (e.g., 'zip', 'tar.gz')
        """
        return ''

    def file_extension(self) -> str:
        """
        Get file extension for this archive format.
        
        Returns:
            File extension
        """
        return self.format()

    def archive_info(self) -> Dict[str, Any]:
        """
        Get archive information.
        
        Returns:
            Dictionary with archive details
        """
        name = ''
        if self._filename:
            parts = self._filename.split('/')
            name = parts[-1] if parts else ''
        
        return {
            'name': name,
            'path': self._filename or '',
            'type': self._type or '',
        }

    def debug(self, message: str):
        """
        Log debug message.
        
        Args:
            message: Debug message
        """
        if self.logger and hasattr(self.logger, 'debug'):
            self.logger.debug(message)

