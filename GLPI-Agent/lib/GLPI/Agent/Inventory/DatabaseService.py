"""
GLPI Agent Inventory DatabaseService - Python Implementation

This module provides methods to support database service inventory.
"""

import re
from typing import Optional, Dict, Any, List


class DatabaseService:
    """
    Database service inventory class.
    
    Provides methods to manage database service information including
    databases, sizes, and metadata.
    """
    
    def __init__(self, 
                 type: Optional[str] = None,
                 name: Optional[str] = None,
                 version: Optional[str] = None,
                 manufacturer: Optional[str] = None,
                 port: Optional[int] = None,
                 is_active: Optional[bool] = None,
                 last_boot_date: Optional[str] = None,
                 last_backup_date: Optional[str] = None,
                 **kwargs):
        """
        Constructor for DatabaseService.
        
        Args:
            type: Database service type
            name: Database service name
            version: Database service version
            manufacturer: Database service manufacturer
            port: Database service port
            is_active: Whether the service is active
            last_boot_date: Last boot date (format: YYYY-MM-DD HH:MM:SS)
            last_backup_date: Last backup date (format: YYYY-MM-DD HH:MM:SS)
        """
        self._type = type
        self._name = name
        self._version = version
        self._manufacturer = manufacturer
        self._port = port
        self._path = None
        self._size = None
        self._is_active = is_active
        self._is_onbackup = None
        self._last_boot_date = None
        self._last_backup_date = None
        self._databases = []
        
        # Validate and set date fields
        date_fields = {
            'last_boot_date': last_boot_date,
            'last_backup_date': last_backup_date
        }
        
        for field_name, field_value in date_fields.items():
            if field_value and self._validate_datetime(field_value):
                setattr(self, f'_{field_name}', field_value)
    
    @staticmethod
    def _validate_datetime(value: str) -> bool:
        """
        Validate datetime format: YYYY-MM-DD HH:MM:SS
        
        Args:
            value: Datetime string to validate
            
        Returns:
            True if valid format, False otherwise
        """
        pattern = r'^(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2}):(\d{2})$'
        return bool(re.match(pattern, value))
    
    def entry(self) -> Dict[str, Any]:
        """
        Return the suitable entry to be inserted in GLPI Agent Inventory.
        
        Returns:
            Dictionary with database service information
        """
        entry = {
            'TYPE': self._type,
            'NAME': self._name,
            'VERSION': self._version,
            'MANUFACTURER': self._manufacturer,
        }
        
        # Add optional fields if defined
        optional_fields = [
            'PORT', 'PATH', 'SIZE', 'IS_ACTIVE', 
            'IS_ONBACKUP', 'LAST_BOOT_DATE', 'LAST_BACKUP_DATE'
        ]
        
        for field in optional_fields:
            attr_name = f'_{field.lower()}'
            value = getattr(self, attr_name, None)
            if value is not None:
                entry[field] = value
        
        # Add found databases
        if self._databases:
            entry['DATABASES'] = self._databases
        
        return entry
    
    def addDatabase(self,
                   name: Optional[str] = None,
                   size: Optional[int] = None,
                   is_active: Optional[bool] = None,
                   is_onbackup: Optional[bool] = None,
                   creation_date: Optional[str] = None,
                   update_date: Optional[str] = None,
                   last_backup_date: Optional[str] = None,
                   **kwargs) -> None:
        """
        Add a database to the database service.
        
        Args:
            name: Database name
            size: Database size
            is_active: Whether the database is active
            is_onbackup: Whether the database is on backup
            creation_date: Database creation date (format: YYYY-MM-DD HH:MM:SS)
            update_date: Database update date (format: YYYY-MM-DD HH:MM:SS)
            last_backup_date: Last backup date (format: YYYY-MM-DD HH:MM:SS)
        """
        database = {}
        
        # Add non-date fields
        simple_fields = {
            'name': name,
            'size': size,
            'is_active': is_active,
            'is_onbackup': is_onbackup
        }
        
        for field_name, field_value in simple_fields.items():
            if field_value is not None:
                database[field_name.upper()] = field_value
        
        # Add date fields with validation
        date_fields = {
            'creation_date': creation_date,
            'update_date': update_date,
            'last_backup_date': last_backup_date
        }
        
        for field_name, field_value in date_fields.items():
            if field_value and self._validate_datetime(field_value):
                database[field_name.upper()] = field_value
        
        self._databases.append(database)
    
    def size(self, size: Optional[int] = None) -> Optional[int]:
        """
        Set or get the database service storage size.
        
        Args:
            size: Size to set (optional)
            
        Returns:
            Current size value
        """
        if size is not None:
            self._size = size
        
        return self._size