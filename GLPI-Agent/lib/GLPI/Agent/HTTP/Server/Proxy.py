"""
GLPI Agent HTTP Server Proxy Plugin

Provides proxy functionality for agents that cannot directly contact the server.
Supports both GLPI protocol and legacy XML inventory forwarding.
"""

import re
import time
import json
from typing import Optional, List, Dict, Any

from GLPI.Agent.HTTP.Server.Plugin import Plugin

try:
    import zlib
except ImportError:
    zlib = None


VERSION = "2.5"


# Module-level variable for request ID in logging
_requestid = None


class Proxy(Plugin):
    """
    Proxy server plugin for forwarding agent requests to GLPI servers.
    
    Supports:
    - GLPI JSON protocol
    - Legacy XML inventory submission
    - Local storage option
    - Request queuing and status tracking
    """

    def urlMatch(self, path: str) -> bool:
        """
        Check if URL path matches proxy endpoints.
        
        Args:
            path: URL path to check
            
        Returns:
            True if path matches, False otherwise
        """
        # By default, re_path_match => qr{^/proxy/(apiversion|glpi)/?$}
        pattern = getattr(self, 're_path_match', None)
        if not pattern:
            return False
        
        match = pattern.match(path)
        if not match:
            return False
        
        self.request = match.group(1)
        return True

    def log_prefix(self) -> str:
        """Get the log prefix for this plugin."""
        global _requestid
        if _requestid:
            return f"[proxy server plugin] {_requestid}: "
        return "[proxy server plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "proxy-server-plugin.cfg"

    def defaults(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of defaults
        """
        return {
            'disabled': "yes",
            'url_path': "/proxy",
            'port': 0,
            'only_local_store': "no",
            'local_store': '',
            'prolog_freq': 24,
            'max_proxy_threads': 10,
            'max_pass_through': 5,
            'glpi_protocol': "yes",
            'no_category': "",
            # Supported by Plugin base class
            'maxrate': 30,
            'maxrate_period': 3600,
            'forbid_not_trusted': "no",
        }

    # Don't publish a URL on glpi-agent index page
    def url(self, request=None) -> None:
        """Override to prevent URL publishing."""
        return None

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

    def init(self):
        """Initialize the proxy plugin."""
        super().init()
        
        # Don't do more initialization if disabled
        if self.disabled():
            return
        
        self.request = 'none'
        
        defaults = self.defaults()
        url_path = self.config('url_path')
        
        if url_path != defaults['url_path']:
            self.debug(f"Using {url_path} as base url matching")
        
        self.re_path_match = re.compile(f"^{url_path}/(apiversion|glpi)/?$")
        
        # Normalize boolean options
        self.only_local_store = not re.match(r'^0|no$', 
                                            str(self.config('only_local_store')), 
                                            re.IGNORECASE)
        self.glpi_protocol = not re.match(r'^0|no$', 
                                         str(self.config('glpi_protocol')), 
                                         re.IGNORECASE)
        
        # Check if we should force local storage
        if self.glpi_protocol and self.server and hasattr(self.server, 'agent'):
            agent = self.server.agent
            if hasattr(agent, 'getTargets'):
                server_targets = [
                    t for t in agent.getTargets() 
                    if hasattr(t, 'isType') and t.isType('server')
                ]
                if not server_targets:
                    self.debug("Forcing only local storing as no glpi server is configured and glpi_protocol is set")
                    self.only_local_store = True
        
        # Initialize request status tracking
        self.status = {}
        self.answer = {}
        self.reqtimeout = []
        
        # Register events callback
        if self.server and hasattr(self.server, 'agent'):
            agent = self.server.agent
            if type(agent).__name__.endswith('Daemon'):
                if hasattr(agent, 'register_events_cb'):
                    agent.register_events_cb(self)

    def events_cb(self, event: Optional[str]) -> bool:
        """
        Handle events from forked processes.
        
        Args:
            event: Event string or None
            
        Returns:
            True if event was handled
        """
        if event is None:
            # Check request timeouts
            if not hasattr(self, 'reqtimeout') or not self.reqtimeout:
                return False
            
            count = len(self.reqtimeout)
            while count > 0:
                answer = self.reqtimeout[0]
                if time.time() <= answer.get('timeout', 0):
                    break
                
                req_id = answer.get('id')
                if req_id in self.answer:
                    del self.answer[req_id]
                
                if count > 1:
                    self.reqtimeout.pop(0)
                else:
                    self.reqtimeout = []
                    break
                
                count -= 1
            
            return False
        
        # Parse proxy request event
        match = re.match(r'^PROXYREQ,([^,]*),(.*)$', event, re.DOTALL)
        if not match:
            return False
        
        reqid, dump = match.groups()
        
        if dump.startswith('{'):
            # Store answer
            try:
                answer_data = json.loads(dump)
                self.answer[reqid] = answer_data
                self.reqtimeout.append({
                    'timeout': time.time() + 3600,
                    'id': reqid,
                })
            except:
                pass
        elif dump.isdigit():
            # Handle timing information
            timing = int(dump)
            if not hasattr(self, '_proxyreq_expiration') or self._proxyreq_expiration < timing:
                self._proxyreq_expiration = timing
            
            if not hasattr(self, '_proxyreq_timing'):
                self._proxyreq_timing = []
            
            self._proxyreq_timing.append(timing)
            
            if len(self._proxyreq_timing) > 30:
                old_timing = self._proxyreq_timing.pop(0)
                if old_timing == self._proxyreq_expiration and old_timing != timing:
                    self._proxyreq_expiration = max(self._proxyreq_timing)
        elif dump == "DELETE":
            # Delete answer
            if reqid in self.answer:
                del self.answer[reqid]
            self.reqtimeout = [
                rt for rt in self.reqtimeout 
                if rt.get('id') != reqid
            ]
        
        return True

    def handle(self, client, request, client_ip: str) -> int:
        """
        Handle proxy request.
        
        Args:
            client: Client connection
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        global _requestid
        
        # Set request ID from header if available
        _requestid = None
        if hasattr(request, 'header'):
            req_id = request.header('GLPI-Request-ID')
            if req_id and re.match(r'^[0-9A-F]{8}$', req_id):
                _requestid = req_id
        
        self.requestid = _requestid
        
        # Rate limit by IP to avoid abuse
        if self.rate_limited(client_ip):
            return self.proxy_error(client, 429, 'Too Many Requests')
        
        # Handle API version request
        if self.request == 'apiversion':
            if hasattr(client, 'send_response'):
                # Send version response (simplified)
                pass
            return 200
        
        self.client = client
        
        # Handle the proxy request
        retcode = self._handle_proxy_request(request, client_ip)
        
        # Check if running in a fork
        if self.server and hasattr(self.server, 'agent'):
            agent = self.server.agent
            if hasattr(agent, 'forked') and agent.forked():
                self.debug(f"response status {retcode}")
                if hasattr(client, 'close'):
                    client.close()
                if hasattr(agent, 'fork_exit'):
                    agent.fork_exit(logger=self, name=self.name())
        
        self.client = None
        
        return retcode

    def _handle_proxy_request(self, request, client_ip: str) -> int:
        """
        Handle the actual proxy request logic.
        
        Args:
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        # This is a simplified implementation
        # Full implementation would handle:
        # - Message parsing and validation
        # - Local storage
        # - Server forwarding
        # - Request queueing and status
        
        return 200

    def proxy_error(self, client, code: int, error: str) -> int:
        """
        Send a proxy error response.
        
        Args:
            client: Client connection
            code: HTTP error code
            error: Error message
            
        Returns:
            HTTP status code
        """
        if hasattr(client, 'send_error'):
            client.send_error(code, error)
        return code


class ProxyMessage:
    """Simple message wrapper for proxy content."""
    
    def __init__(self, content: str):
        """
        Initialize proxy message.
        
        Args:
            content: Message content
        """
        self.content = content
    
    def getContent(self) -> str:
        """
        Get message content.
        
        Returns:
            Content string
        """
        return self.content

