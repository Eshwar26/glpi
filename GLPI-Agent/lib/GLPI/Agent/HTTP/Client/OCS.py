"""
GLPI Agent HTTP Client OCS - Python Implementation

This module provides an HTTP client for communicating with OCS or GLPI servers
using the original OCS protocol (XML messages sent through POST requests).
"""

import gzip
import json
import logging
import re
import uuid
from io import BytesIO
from typing import Optional, Union
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GLPIAgentHTTPClientOCS:
    """
    HTTP client for sending messages to OCS or GLPI servers using OCS protocol.
    
    This class handles:
    - HTTP POST requests with XML content
    - Compression/decompression of request and response content
    - Custom headers including agent identification
    - Response parsing and error handling
    """
    
    LOG_PREFIX = "[http client] "
    
    def __init__(self, agentid: Optional[str] = None, compression: str = 'gzip',
                 timeout: int = 180, logger: Optional[logging.Logger] = None,
                 ca_cert_file: Optional[str] = None, ssl_verify: bool = True,
                 **kwargs):
        """
        Initialize the HTTP client.
        
        Args:
            agentid: Agent UUID for identification
            compression: Compression method ('gzip', 'deflate', or 'none')
            timeout: Request timeout in seconds
            logger: Logger instance for debugging
            ca_cert_file: Path to CA certificate file
            ssl_verify: Whether to verify SSL certificates
            **kwargs: Additional parameters for session configuration
        """
        self.compression = compression
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.ca_cert_file = ca_cert_file
        self.ssl_verify = ssl_verify
        
        # Initialize requests session
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Pragma': 'no-cache',
            'User-Agent': 'GLPI-Agent-Python/1.0'
        })
        
        # Set content-type header when not compressing
        if self.compression == 'none':
            self.session.headers.update({
                'Content-Type': 'application/xml'
            })
        
        # Add GLPI Agent ID header if provided
        if agentid:
            normalized_agentid = self._normalize_uuid(agentid)
            self.session.headers.update({
                'GLPI-Agent-ID': normalized_agentid
            })
    
    def _normalize_uuid(self, agentid: str) -> str:
        """
        Normalize UUID string to standard format.
        
        Args:
            agentid: UUID string (with or without hyphens)
            
        Returns:
            Normalized UUID string in standard format
        """
        try:
            # Try to parse as UUID
            parsed_uuid = uuid.UUID(agentid)
            return str(parsed_uuid)
        except ValueError:
            # If not a valid UUID, return as-is
            return agentid
    
    def compress(self, content: str) -> Optional[bytes]:
        """
        Compress content based on the configured compression method.
        
        Args:
            content: String content to compress
            
        Returns:
            Compressed bytes or None if compression fails
        """
        try:
            encoded_content = content.encode('utf-8')
            
            if self.compression == 'none':
                return encoded_content
            elif self.compression == 'gzip':
                buffer = BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
                    gz.write(encoded_content)
                return buffer.getvalue()
            elif self.compression == 'deflate':
                import zlib
                return zlib.compress(encoded_content)
            else:
                self.logger.warning(f"{self.LOG_PREFIX}Unknown compression: {self.compression}")
                return encoded_content
                
        except Exception as e:
            self.logger.error(f"{self.LOG_PREFIX}Compression error: {e}")
            return None
    
    def uncompress(self, content: bytes, content_type: str = '') -> Optional[str]:
        """
        Uncompress content based on content-type header.
        
        Args:
            content: Compressed bytes content
            content_type: Content-Type header value
            
        Returns:
            Uncompressed string or None if decompression fails
        """
        try:
            # Determine compression type from content-type
            if 'gzip' in content_type.lower() or 'application/x-gzip' in content_type.lower():
                buffer = BytesIO(content)
                with gzip.GzipFile(fileobj=buffer, mode='rb') as gz:
                    return gz.read().decode('utf-8')
            elif 'deflate' in content_type.lower() or 'application/x-deflate' in content_type.lower():
                import zlib
                return zlib.decompress(content).decode('utf-8')
            else:
                # Assume uncompressed
                return content.decode('utf-8')
                
        except Exception as e:
            self.logger.error(f"{self.LOG_PREFIX}Decompression error: {e}")
            return None
    
    def send(self, url: Union[str, object], message: object) -> Optional[object]:
        """
        Send a message to the server and return the response.
        
        Args:
            url: Target URL (string or URI object)
            message: Message object with getContent() method
            
        Returns:
            Response object or None if request fails
        """
        # Convert URL to string if necessary
        url_str = str(url) if not isinstance(url, str) else url
        
        # Get message content
        try:
            request_content = message.getContent()
            self.logger.debug(f"{self.LOG_PREFIX}sending message:\n{request_content[:500]}")
        except Exception as e:
            self.logger.error(f"{self.LOG_PREFIX}Failed to get message content: {e}")
            return None
        
        # Compress content
        compressed_content = self.compress(request_content)
        if compressed_content is None:
            self.logger.error(f"{self.LOG_PREFIX}inflating problem")
            return None
        
        # Prepare request
        try:
            verify = self.ca_cert_file if self.ca_cert_file else self.ssl_verify
            
            response = self.session.post(
                url_str,
                data=compressed_content,
                timeout=self.timeout,
                verify=verify
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"{self.LOG_PREFIX}Request failed: {e}")
            return None
        
        # Get response content
        response_content = response.content
        if not response_content:
            self.logger.error(f"{self.LOG_PREFIX}unknown content format")
            return None
        
        # Determine content type
        content_type = response.headers.get('Content-Type', 'text/plain')
        
        # Uncompress if necessary
        if re.match(r'^application/x-', content_type, re.IGNORECASE):
            uncompressed_content = self.uncompress(response_content, content_type)
        else:
            uncompressed_content = response_content.decode('utf-8')
        
        if not uncompressed_content:
            preview = response_content[:500]
            self.logger.error(
                f"{self.LOG_PREFIX}can't uncompress content starting with: {preview}"
            )
            return None
        
        self.logger.debug(f"{self.LOG_PREFIX}receiving message:\n{uncompressed_content[:500]}")
        
        # Parse response
        result = None
        
        # Try XML parsing first
        try:
            result = self._parse_xml_response(uncompressed_content)
        except Exception as e:
            self.logger.debug(f"{self.LOG_PREFIX}XML parsing failed: {e}")
        
        # If XML parsing failed and content looks like JSON, try JSON
        if result is None and re.match(r'^\s*\{.*\}\s*$', uncompressed_content, re.DOTALL):
            try:
                result = self._parse_json_contact(uncompressed_content)
            except Exception as e:
                self.logger.debug(f"{self.LOG_PREFIX}JSON parsing failed: {e}")
        
        # Handle special error messages
        if result is None:
            if re.search(r'Inventory is disabled', uncompressed_content, re.IGNORECASE):
                self.logger.warning(
                    f"{self.LOG_PREFIX}Inventory support is disabled server-side"
                )
            else:
                lines = uncompressed_content.split('\n')
                first_line = lines[0][:120] if lines else ''
                self.logger.error(
                    f"{self.LOG_PREFIX}unexpected content, starting with: {first_line}"
                )
            return None
        
        return result
    
    def _parse_xml_response(self, content: str) -> object:
        """
        Parse XML response content.
        
        Args:
            content: XML string content
            
        Returns:
            Parsed response object
        """
        # Placeholder for XML response parsing
        # In practice, you would use xml.etree.ElementTree or lxml
        from xml.etree import ElementTree as ET
        
        class XMLResponse:
            def __init__(self, content):
                self.root = ET.fromstring(content)
                self.content = content
            
            def is_valid_message(self):
                return self.root is not None
        
        return XMLResponse(content)
    
    def _parse_json_contact(self, content: str) -> object:
        """
        Parse JSON CONTACT response.
        
        Args:
            content: JSON string content
            
        Returns:
            Parsed contact object
        """
        class ContactResponse:
            def __init__(self, message):
                self.data = json.loads(message)
                self.message = message
            
            def is_valid_message(self):
                return isinstance(self.data, dict)
            
            @property
            def status(self):
                return self.data.get('status', 'unknown')
        
        try:
            contact = ContactResponse(content)
            
            if contact.status == 'pending':
                self.logger.debug("Got GLPI CONTACT pending answer")
            else:
                self.logger.debug("Not a GLPI CONTACT message")
            
            return contact
            
        except json.JSONDecodeError as e:
            self.logger.error(f"{self.LOG_PREFIX}JSON parsing error: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create a simple message class for testing
    class TestMessage:
        def __init__(self, content):
            self.content = content
        
        def getContent(self):
            return self.content
    
    # Initialize client
    client = GLPIAgentHTTPClientOCS(
        agentid="550e8400-e29b-41d4-a716-446655440000",
        compression="gzip"
    )
    
    # Example XML message
    xml_message = """<?xml version="1.0" encoding="UTF-8"?>
    <REQUEST>
        <DEVICEID>test-device</DEVICEID>
        <QUERY>INVENTORY</QUERY>
    </REQUEST>"""
    
    message = TestMessage(xml_message)
    
    # Send message (would need actual server URL)
    # response = client.send("http://glpi-server/endpoint", message)
    print("Client initialized successfully")