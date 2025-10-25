"""
GLPI Agent HTTP Server Inventory Plugin

Provides remote inventory capability through HTTP API.
Clients can request sessions and retrieve inventory data.
"""

import re
import time
from typing import Optional

from GLPI.Agent.HTTP.Server.Plugin import Plugin

try:
    from GLPI.Agent.Task.Inventory import Inventory as InventoryTask
except ImportError:
    InventoryTask = None

try:
    from GLPI.Agent.Target.Listener import Listener
except ImportError:
    Listener = None


VERSION = "1.1"


class Inventory(Plugin):
    """
    Inventory server plugin for remote inventory requests.
    
    Provides API endpoints:
    - /inventory/session - Create session and get nonce
    - /inventory/get - Get inventory with authentication
    - /inventory/apiversion - Get API version
    """

    def urlMatch(self, path: str) -> bool:
        """
        Check if URL path matches inventory endpoints.
        
        Args:
            path: URL path to check
            
        Returns:
            True if path matches, False otherwise
        """
        # By default, re_path_match => qr{^/inventory/(session|get|apiversion)$}
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
        return "[inventory server plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "inventory-server-plugin.cfg"

    def defaults(self) -> dict:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of defaults
        """
        return {
            'disabled': "yes",
            'url_path': "/inventory",
            'port': 0,
            'token': None,
            'session_timeout': 60,
            'no_compress': "no",
            # Supported by Plugin base class
            'maxrate': 30,
            'maxrate_period': 3600,
            'forbid_not_trusted': "no",
        }

    # Don't publish a URL on glpi-agent index page
    def url(self, request=None) -> None:
        """Override to prevent URL publishing."""
        return None

    def init(self):
        """Initialize the inventory plugin."""
        super().init()
        
        # Don't do more initialization if disabled
        if self.disabled():
            return
        
        # Check token is set if plugin is enabled
        if not self.config('token'):
            self.error("Plugin enabled without token in configuration")
            self.disable("Plugin disabled on wrong configuration")
            return
        
        self.request = 'none'
        
        defaults = self.defaults()
        url_path = self.config('url_path')
        
        if url_path != defaults['url_path']:
            self.debug(f"Using {url_path} as base url matching")
        
        self.re_path_match = re.compile(f"^{url_path}/(session|get|apiversion)$")
        
        # Always use a dedicated Listener target for this plugin
        if not hasattr(self, 'target') and Listener is not None:
            vardir = None
            if self.server and hasattr(self.server, 'agent'):
                agent = self.server.agent
                if hasattr(agent, 'config') and hasattr(agent.config, 'vardir'):
                    vardir = agent.config.vardir
            
            self.target = Listener(
                logger=self.logger,
                basevardir=vardir,
            )
        
        # Normalize no_compress
        self.no_compress = not re.match(r'^0|no$', 
                                       str(self.config('no_compress')), 
                                       re.IGNORECASE)

    def handle(self, client, request, client_ip: str) -> int:
        """
        Handle inventory request.
        
        Args:
            client: Client connection
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        logger = self.logger
        target = getattr(self, 'target', None)
        
        # Rate limit by IP to avoid abuse
        if self.rate_limited(client_ip):
            if hasattr(client, 'send_error'):
                client.send_error(429)  # Too Many Requests
            return 429
        
        # Handle API version request
        if self.request == 'apiversion':
            if hasattr(client, 'send_response'):
                # Send version response (simplified)
                return 200
            return 200
        
        # Get request ID header
        request_id = None
        if hasattr(request, 'header'):
            request_id = request.header('X-Request-ID')
        
        if not request_id:
            self.info(f"No mandatory X-Request-ID header provided in {self.request} request from {client_ip}")
            if hasattr(client, 'send_error'):
                client.send_error(403, 'No session available')
            return 403
        
        remoteid = f"{{{request_id}}}@[{client_ip}]"
        
        # Get or create session
        session = None
        if target and hasattr(target, 'session'):
            session = target.session(
                remoteid=remoteid,
                timeout=self.config('session_timeout'),
            )
        
        if not session:
            self.info(f"No session available for {remoteid}")
            if hasattr(client, 'send_error'):
                client.send_error(403, 'No session available')
            return 403
        
        self.debug(f"Session sid for {remoteid}: {session.sid()}")
        
        # Handle session request
        if self.request == 'session':
            nonce = session.nonce() if hasattr(session, 'nonce') else None
            
            if not nonce:
                self.info(f"Session setup failure for {remoteid}")
                if hasattr(client, 'send_error'):
                    client.send_error(500, 'Session failure')
                return 500
            
            # Send response with nonce (simplified)
            if hasattr(client, 'send_response'):
                # Would send nonce in X-Auth-Nonce header
                pass
            
            return 200
        
        # Handle inventory get request
        authorization = False
        if hasattr(session, 'authorized'):
            payload = None
            if hasattr(request, 'header'):
                payload = request.header('X-Auth-Payload') or ''
            
            authorization = session.authorized(
                token=self.config('token'),
                payload=payload
            )
        
        # Cleanup the session
        if target and hasattr(target, 'clean_session'):
            target.clean_session(session)
        
        if not authorization:
            self.info(f"unauthorized remote inventory request for {remoteid}")
            if hasattr(client, 'send_error'):
                client.send_error(403)
            return 403
        
        self.debug(f"remote inventory request for {remoteid}")
        
        # Run inventory task
        if InventoryTask and self.server and hasattr(self.server, 'agent'):
            agent = self.server.agent
            
            task = InventoryTask(
                logger=logger,
                target=target,
                deviceid=getattr(agent, 'deviceid', None),
                datadir=getattr(agent, 'datadir', None),
                config=getattr(agent, 'config', None),
            )
            
            # Run task
            done = False
            if hasattr(task, 'run'):
                done = task.run()
            
            if not done:
                self.error("Failed to run inventory")
                if hasattr(client, 'send_error'):
                    client.send_error(500, "Inventory failure")
                return 500
            
            # Get inventory data
            data = None
            if target and hasattr(target, 'inventory_xml'):
                data = target.inventory_xml()
            
            if data:
                # Handle compression if needed
                content_type = 'application/xml'
                
                # Check compression support
                accept = []
                if hasattr(request, 'header'):
                    accept_header = request.header('accept') or ''
                    accept = [a.strip() for a in accept_header.split(',')]
                
                # Would compress data here if needed
                
                # Send response (simplified)
                if hasattr(client, 'send_response'):
                    pass
                
                self.info(f"Inventory returned to {remoteid}")
                return 200
        
        return 500

    def timer_event(self) -> Optional[int]:
        """
        Handle timer events for session cleanup.
        
        Returns:
            Next timer timeout or None
        """
        if hasattr(self, 'target') and self.target:
            if hasattr(self.target, 'keep_sessions'):
                return self.target.keep_sessions()
        return None

