"""
GLPI Agent HTTP Server Test Plugin

A simple test plugin demonstrating the plugin system.
Responds to test requests with a 200 status code.
"""

import re
from GLPI.Agent.HTTP.Server.Plugin import Plugin


class Test(Plugin):
    """
    Test server plugin for demonstration and testing.
    
    Accepts any request matching /test/* and returns HTTP 200.
    """

    def urlMatch(self, path: str) -> bool:
        """
        Check if URL path matches /test/*.
        
        Args:
            path: URL path to check
            
        Returns:
            True if path matches, False otherwise
        """
        self.debug(f"Matching on {path} ?")
        
        match = re.match(r'^/test/([\w\d/-]+)?$', path)
        if match:
            self.test = match.group(1)
            self.debug2(f"Found matching on {path}")
            return True
        
        return False

    def handle(self, client, request, client_ip: str) -> int:
        """
        Handle a test request.
        
        Args:
            client: Client connection
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code (always 200)
        """
        configtest = getattr(self, 'configtest', 'none')
        test = getattr(self, 'test', '')
        
        self.info(f"Test request from {client_ip}: /test/{test} (config: {configtest})")
        
        # Clean up test attribute
        if hasattr(self, 'test'):
            delattr(self, 'test')
        
        # Send 200 response
        if hasattr(client, 'send_response'):
            client.send_response(200)
        
        return 200

    def log_prefix(self) -> str:
        """Get the log prefix for this plugin."""
        return "[server test plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "server-test-plugin.cfg"

    def defaults(self) -> dict:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of defaults
        """
        return {
            'disabled': "yes",
            'configtest': "test",
            'port': 0,
            'forbid_not_trusted': "no",
        }

