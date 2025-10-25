#!/usr/bin/env python3
"""
GLPI Agent Protocol Message - Python Implementation

Base class for JSON messages sent and received by the agent.
Handles encoding, decoding, and manipulation of protocol messages.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union


class ProtocolMessage:
    """
    Base class for GLPI Agent protocol messages.
    
    Handles JSON message encoding/decoding and provides
    convenient access to message fields.
    """
    
    def __init__(self, **params: Any):
        """
        Initialize protocol message.
        
        Args:
            **params: Parameters including:
                - message: Message content (dict or JSON string)
                - logger: Logger instance (optional)
                - file: File path to load message from
                - supported_params: List of parameters to load from params
        """
        self._message: Dict[str, Any] = params.get('message', {})
        self.logger = params.get('logger')
        self._id: Optional[str] = None
        
        # Parse message if string
        if isinstance(self._message, str):
            self.set(self._message)
        elif not isinstance(self._message, dict):
            self._message = {}
        
        # Load from file if specified
        file_path = params.get('file')
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        self.set(content)
            except (IOError, OSError):
                pass
        
        # Load supported params if not a server response
        if not self.status() and params.get('supported_params'):
            message = self.get()
            for param in params['supported_params']:
                if param in params and params[param] is not None:
                    message[param] = params[param]
    
    @staticmethod
    def _convert(data: Any) -> Any:
        """
        Recursively convert all keys in dict to lowercase.
        
        Args:
            data: Data structure to convert
            
        Returns:
            Converted data structure
        """
        if not isinstance(data, dict):
            return data
        
        converted = {}
        for key, value in data.items():
            # Recursively convert nested structures
            if isinstance(value, dict):
                value = ProtocolMessage._convert(value)
            elif isinstance(value, list):
                value = [ProtocolMessage._convert(item) for item in value]
            
            # Convert key to lowercase
            converted[key.lower()] = value
        
        return converted
    
    def converted(self) -> Dict[str, Any]:
        """
        Get message with all keys converted to lowercase.
        
        Returns:
            Message dict with lowercase keys
        """
        return self._convert(self._message)
    
    def getRawContent(self) -> str:
        """
        Get message as compact JSON string.
        
        Returns:
            JSON string without formatting
        """
        if not isinstance(self._message, dict):
            return str(self._message)
        
        return json.dumps(self._message, ensure_ascii=False)
    
    def getContent(self) -> str:
        """
        Get message as pretty-printed JSON string.
        
        Returns:
            Formatted JSON string with indentation
        """
        if not isinstance(self._message, dict):
            return str(self._message)
        
        return json.dumps(
            self.converted(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True
        )
    
    def set(self, message: Union[str, Dict]) -> Optional[Dict]:
        """
        Set message content from dict or JSON string.
        
        Args:
            message: Message as dict or JSON string
            
        Returns:
            Set message dict or None
        """
        if message is None:
            return None
        
        if isinstance(message, dict):
            self._message = message
        else:
            try:
                self._message = json.loads(message)
            except json.JSONDecodeError:
                self._message = {}
        
        return self._message
    
    def get(self, key: Optional[str] = None) -> Any:
        """
        Get message or specific field.
        
        Args:
            key: Optional field name to retrieve
            
        Returns:
            Entire message dict if no key, or field value
        """
        if self._message is None:
            return None
        
        if key is not None:
            return self._message.get(key)
        
        return self._message
    
    def merge(self, **params: Any) -> None:
        """
        Merge parameters into message.
        
        Args:
            **params: Key-value pairs to merge
        """
        for key, value in params.items():
            self._message[key] = value
    
    def delete(self, key: str) -> Any:
        """
        Delete field from message.
        
        Args:
            key: Field name to delete
            
        Returns:
            Deleted value or None
        """
        if key is None or self._message is None:
            return None
        
        return self._message.pop(key, None)
    
    def expiration(self, expiration: Optional[Union[str, int]] = None) -> int:
        """
        Get or set expiration time in seconds.
        
        Args:
            expiration: Expiration string (e.g., "30s", "5m", "2h", "1d") or seconds
            
        Returns:
            Expiration in seconds (0 if invalid or not set)
        """
        if expiration is not None:
            # Setting expiration
            if not self._message:
                return 0
            
            # Validate format
            if isinstance(expiration, int):
                expiration = str(expiration)
            
            if not re.match(r'^\d+[dshm]?$', str(expiration)):
                return 0
            
            self._message['expiration'] = expiration
            return self._parse_expiration(expiration)
        
        # Getting expiration
        if not self._message or 'expiration' not in self._message:
            return 0
        
        return self._parse_expiration(self._message['expiration'])
    
    @staticmethod
    def _parse_expiration(exp_str: Union[str, int]) -> int:
        """
        Parse expiration string to seconds.
        
        Args:
            exp_str: Expiration string or int
            
        Returns:
            Expiration in seconds
        """
        if isinstance(exp_str, int):
            return exp_str * 3600  # Default to hours
        
        match = re.match(r'^(\d+)([dshm]?)$', str(exp_str))
        if not match:
            return 0
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if not unit:
            return value * 3600  # Default to hours
        elif unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        else:  # 'd'
            return value * 86400
    
    def action(self) -> str:
        """
        Get action from message.
        
        Returns:
            Action string (default: "inventory")
        """
        return self.get('action') or "inventory"
    
    def status(self) -> str:
        """
        Get status from message.
        
        Returns:
            Status string (empty if not set)
        """
        return self.get('status') or ""
    
    def is_valid_message(self) -> bool:
        """
        Check if message is valid (has content and status).
        
        Returns:
            True if valid message
        """
        return bool(self.get() and self.status())
    
    def id(self, message_id: Optional[str] = None) -> Optional[str]:
        """
        Get or set message ID.
        
        Args:
            message_id: ID to set (if provided)
            
        Returns:
            Message ID
        """
        if message_id is not None:
            self._id = message_id
        return self._id
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        status = self.status()
        action = self.action()
        return f"ProtocolMessage(status='{status}', action='{action}')"