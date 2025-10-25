"""
GLPI Agent HTTP Server Basic Authentication Plugin

Provides HTTP Basic Authentication for server plugins.
High priority plugin that runs before others to check credentials.
"""

import base64
import re
from typing import Optional

from GLPI.Agent.HTTP.Server.Plugin import Plugin


VERSION = "1.0"


class BasicAuthentication(Plugin):
    """
    Basic Authentication server plugin.
    
    Enforces HTTP Basic Authentication on configured URL patterns.
    Has high priority (100) to run before other plugins.
    """

    def priority(self) -> int:
        """
        Get plugin priority.
        
        Authentication should be passed before other plugins.
        
        Returns:
            Priority value (100 - highest)
        """
        return 100

    def urlMatch(self, path: str) -> bool:
        """
        Check if URL path matches authentication pattern.
        
        Args:
            path: URL path to check
            
        Returns:
            True if path matches, False otherwise
        """
        # By default, re_path_match => qr{^.*$}
        pattern = getattr(self, 're_path_match', re.compile(r'^.*$'))
        match = pattern.match(path)
        
        if not match:
            return False
        
        self.request = match.group(1) if match.lastindex else path
        return True

    def log_prefix(self) -> str:
        """Get the log prefix for this plugin."""
        return "[basic authentication server plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "basic-authentication-server-plugin.cfg"

    def defaults(self) -> dict:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of defaults
        """
        return {
            'disabled': "yes",
            'url_path_regexp': ".*",
            'port': 0,
            'realm': None,
            'user': None,
            'password': None,
            # Supported by Plugin base class
            'maxrate': 600,
            'maxrate_period': 600,
            'forbid_not_trusted': "no",
        }

    def init(self):
        """Initialize the authentication plugin."""
        super().init()
        
        # Don't do more initialization if disabled
        if self.disabled():
            return
        
        # Check basic authentication is well setup if plugin is enabled
        if not self.config('user') or not self.config('password'):
            self.error("Plugin enabled without basic authentication fully setup")
            self.disable("Plugin disabled on wrong configuration")
            return
        
        defaults = self.defaults()
        url_path_regexp = self.config('url_path_regexp')
        
        if url_path_regexp != defaults['url_path_regexp']:
            self.debug(f"Using '{url_path_regexp}' as base url matching regexp")
        
        self.re_path_match = re.compile(f"^{url_path_regexp}$")
        
        # Setup a default realm if not set
        if not self.config('realm'):
            self.config('realm', "GLPI Agent")

    def supported_method(self, method: str) -> bool:
        """
        Check if request method is supported.
        
        Args:
            method: HTTP method
            
        Returns:
            True if supported (GET or POST)
        """
        if method in ('GET', 'POST'):
            return True
        
        self.error(f"invalid request type: {method}")
        return False

    def handle(self, client, request, client_ip: str) -> int:
        """
        Handle authentication request.
        
        Args:
            client: Client connection
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code (0 if authorized, 401/403 if not)
        """
        # Rate limit by IP to avoid abuse
        if self.rate_limited(client_ip):
            if hasattr(client, 'send_error'):
                client.send_error(429)  # Too Many Requests
            return 429
        
        # Check for Authorization header
        auth = request.header('Authorization') if hasattr(request, 'header') else None
        
        if not auth:
            # Send 401 Unauthorized with WWW-Authenticate header
            realm = self.config('realm')
            
            try:
                # Try to create response with headers
                import http.client
                response_class = getattr(http.client, 'HTTPResponse', None)
                
                if hasattr(client, 'send_response'):
                    # Simple response sending
                    if hasattr(client, 'send_error'):
                        client.send_error(401, 'Unauthorized')
                    else:
                        client.send_response(401)
                
            except:
                pass
            
            return 401
        
        # Return 0 to leave other plugins really handle the request
        if self._authorized(auth):
            return 0
        
        if hasattr(client, 'send_error'):
            client.send_error(403, "Forbidden")
        return 403

    def _authorized(self, auth: str) -> bool:
        """
        Check if authorization credentials are valid.
        
        Args:
            auth: Authorization header value
            
        Returns:
            True if authorized, False otherwise
        """
        # Parse authorization header
        parts = auth.split(" ", 1)
        if len(parts) != 2:
            return False
        
        basic, credential = parts
        
        if not re.match(r'^Basic$', basic, re.IGNORECASE):
            return False
        
        try:
            # Decode base64 credentials
            decoded = base64.b64decode(credential).decode('utf-8')
            user_pass = decoded.split(':', 1)
            
            if len(user_pass) != 2:
                return False
            
            user, password = user_pass
            
            # Check credentials
            return (user == self.config('user') and 
                   password == self.config('password'))
            
        except Exception:
            return False

