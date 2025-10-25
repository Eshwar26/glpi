import json
import requests
from urllib.parse import quote_plus, urlencode, urlparse, parse_qs
from typing import Dict, Any, Optional, List, Union
from http.cookiejar import CookieJar

from .base_http_client import HTTPClient  # Base HTTP client
from .logger import Logger

LOG_PREFIX = "[http client] "

class FusionClient(HTTPClient):
    def __init__(self, **params):
        # Force no compression for Fusion protocol
        params['no_compress'] = True
        super().__init__(**params)
        
        # Initialize cookie jar for session management
        self._cookies = CookieJar()
    
    def _prepareVal(self, val: Any) -> str:
        """Prepare value for URL encoding with truncation"""
        if not val:
            return ''
        
        val_str = str(val)
        if not val_str:
            return ''
        
        # Forbid too long arguments - truncate if URL-encoded length > 1500
        while len(quote_plus(val_str, encoding='utf-8')) > 1500:
            # Remove first 5 chars and add ellipsis
            if len(val_str) <= 5:
                break
            val_str = '…' + val_str[5:]
        
        return quote_plus(val_str, encoding='utf-8')
    
    def send(self, **params) -> Optional[Dict[str, Any]]:
        """Send HTTP request using Fusion protocol"""
        url = params.get('url')
        if not url:
            return None
        
        # Convert to string if URL object
        if hasattr(url, 'geturl'):
            url = url.geturl()
        else:
            url = str(url)
        
        # Determine HTTP method
        method = params.get('method', 'GET')
        if method not in ('GET', 'POST'):
            method = 'GET'
        
        args = params.get('args', {})
        if not args or not args.get('action'):
            return None
        
        # Build URL parameters
        url_params = [f"action={quote_plus(args['action'])}"]
        referer = ''
        
        # Handle POST vs GET URL structure
        if method == 'POST':
            referer = url
            url += '?' + '&'.join(url_params)
            if 'uuid' in args:
                url += f"&uuid={quote_plus(str(args['uuid']))}"
            url += '&method=POST'
        
        # Process all arguments
        for key, value in args.items():
            if isinstance(value, list):
                # Handle array parameters
                for item in value:
                    url_params.append(f"{key}[]={self._prepareVal(item or '')}")
            elif isinstance(value, dict):
                # Handle hash parameters
                for sub_key, sub_value in value.items():
                    url_params.append(f"{key}[{sub_key}]={self._prepareVal(sub_value)}")
            elif key != 'action' and value:
                # Handle scalar parameters (skip action, already added)
                url_params.append(f"{key}={self._prepareVal(value)}")
        
        # For GET requests, add params to URL
        if method == 'GET':
            url += '?' + '&'.join(url_params)
        
        if self.logger:
            self.logger.debug2(url)
        
        # Prepare request
        headers = {}
        data = None
        
        if method == 'POST':
            post_data = '&'.join(url_params)
            if self.logger:
                self.logger.debug2(f"{LOG_PREFIX}POST: {post_data}")
            
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': referer
            })
            data = post_data
        
        # Make request with session (for cookies)
        try:
            if not hasattr(self, '_session'):
                self._session = requests.Session()
                self._session.cookies = self._cookies
            
            if method == 'POST':
                response = self._session.post(url, data=data, headers=headers, **self._get_request_kwargs())
            else:
                response = self._session.get(url, headers=headers, **self._get_request_kwargs())
            
            # Check if request was successful
            if not response.ok:
                if self.logger:
                    self.logger.error(f"{LOG_PREFIX}HTTP {response.status_code}: {response.reason}")
                return None
            
            # Get response content
            content = response.text
            if not content:
                if self.logger:
                    self.logger.error(f"{LOG_PREFIX}Got empty response")
                return None
            
            # Parse JSON response
            try:
                answer = json.loads(content)
                return answer
            except json.JSONDecodeError as e:
                if self.logger:
                    # Show sanitized content start for debugging
                    lines = content.split('\n')
                    starting = ''
                    while lines and len(starting) < 120:
                        line = self._sanitize_string(lines.pop(0))
                        if len(line) < 120:
                            starting += line + '\n'
                        else:
                            starting += line[:120] + ' ...\n'
                    
                    error_msg = f"{LOG_PREFIX}Can't decode JSON content"
                    if starting:
                        error_msg += f", starting with: {starting}"
                        if lines:
                            error_msg += "..."
                    
                    self.logger.error(error_msg)
                return None
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"{LOG_PREFIX}Request failed: {e}")
            return None
    
    def _get_request_kwargs(self) -> Dict[str, Any]:
        """Get common request keyword arguments"""
        kwargs = {
            'timeout': getattr(self, 'timeout', 30),
            'verify': not getattr(self, 'no_ssl_check', False),
        }
        
        # Add proxy if configured
        if hasattr(self, 'proxy') and self.proxy:
            kwargs['proxies'] = {'http': self.proxy, 'https': self.proxy}
        
        # Add SSL cert if configured
        if hasattr(self, 'ssl_cert_file') and self.ssl_cert_file:
            kwargs['cert'] = self.ssl_cert_file
        
        return kwargs
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string for logging (remove control chars, etc.)"""
        if not text:
            return text
        
        # Replace control characters with spaces, keep printable chars
        sanitized = ''.join(c if c.isprintable() or c in '\n\t' else ' ' for c in text)
        return sanitized.strip()