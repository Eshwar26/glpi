"""
GLPI Agent HTTP Server Module

This module provides an embedded HTTP server for the GLPI Agent.
It handles incoming requests, plugin management, SSL support, and authentication.
"""

import os
import sys
import time
import socket
import select
import hashlib
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from typing import Optional, Dict, List, Any, Tuple
import glob
import re
import struct
from io import BytesIO
from collections import namedtuple

try:
    from jinja2 import Template
except ImportError:
    Template = None

try:
    import ipaddress
except ImportError:
    ipaddress = None

from GLPI.Agent import Version
from GLPI.Agent.Logger import Logger
from GLPI.Agent.Tools import Tools
try:
    from GLPI.Agent.Tools.Network import compile as compile_address, isPartOf
except ImportError:
    compile_address = None
    isPartOf = None

try:
    from GLPI.Agent.Event import Event
except ImportError:
    Event = None


# Expire trusted IP/ranges cache after a minute
TRUSTED_CACHE_TIMEOUT = 60

# Limit maximum requests number handled in a keep-alive connection
MAX_KEEP_ALIVE = 8

# Log prefix
LOG_PREFIX = "[http server] "

# HTTP Request structure
HTTPRequest = namedtuple('HTTPRequest', [
    'method', 'path', 'query', 'version', 'headers', 'body', 'client_ip'
])


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for GLPI Agent Server"""
    
    def __init__(self, *args, server=None, **kwargs):
        """Initialize with server reference"""
        self.server_instance = server
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Log message using server's logger"""
        if self.server_instance and hasattr(self.server_instance, 'logger'):
            message = format % args
            self.server_instance.logger.debug(f"{LOG_PREFIX}{message}")
    
    def parse_custom_request(self):
        """Parse HTTP request and return HTTPRequest object"""
        try:
            # Parse request line
            line = self.rfile.readline(self.server.max_request_size if hasattr(self.server, 'max_request_size') else 65537)
            if not line:
                return None
            
            line = line.rstrip(b'\r\n')
            request_line = line.decode('latin-1', errors='replace')
            
            parts = request_line.split(None, 2)
            if len(parts) < 2:
                return None
            
            method = parts[0]
            path_part = parts[1]
            version = parts[2] if len(parts) > 2 else 'HTTP/1.0'
            
            # Parse path and query
            parsed = urlparse(path_part)
            path = unquote(parsed.path)
            query = parsed.query
            
            # Parse headers
            headers = {}
            while True:
                line = self.rfile.readline(65537).rstrip(b'\r\n')
                if not line:
                    break
                
                header_line = line.decode('latin-1', errors='replace')
                if ':' in header_line:
                    key, value = header_line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Read body if Content-Length is specified
            body = b''
            if 'content-length' in headers:
                try:
                    content_length = int(headers['content-length'])
                    if content_length > 0:
                        body = self.rfile.read(content_length)
                except (ValueError, OSError):
                    pass
            
            # Get client IP
            client_ip = self.client_address[0] if self.client_address else 'unknown'
            
            return HTTPRequest(
                method=method,
                path=path,
                query=query,
                version=version,
                headers=headers,
                body=body,
                client_ip=client_ip
            )
        except Exception as e:
            if self.server_instance and hasattr(self.server_instance, 'logger'):
                self.server_instance.logger.error(f"{LOG_PREFIX}Error parsing request: {e}")
            return None
    
    def send_response_data(self, status_code: int, content: bytes = b'', 
                          content_type: str = 'text/html; charset=utf-8',
                          headers: Optional[Dict[str, str]] = None):
        """Send HTTP response"""
        status_text = HTTPStatus(status_code).phrase
        
        # Build response
        response_headers = {
            'Content-Type': content_type,
            'Content-Length': str(len(content)),
            'Connection': 'close',
        }
        
        if headers:
            response_headers.update(headers)
        
        # Send status line
        self.wfile.write(f"HTTP/1.1 {status_code} {status_text}\r\n".encode('latin-1'))
        
        # Send headers
        for key, value in response_headers.items():
            self.wfile.write(f"{key}: {value}\r\n".encode('latin-1'))
        
        self.wfile.write(b'\r\n')
        
        # Send body
        if content:
            self.wfile.write(content)
        
        self.wfile.flush()
    
    def do_GET(self):
        """Handle GET request"""
        self.handle_http_request()
    
    def do_POST(self):
        """Handle POST request"""
        self.handle_http_request()
    
    def handle_http_request(self):
        """Handle HTTP request"""
        request = self.parse_custom_request()
        if not request:
            self.send_response_data(400, b'Bad Request')
            return
        
        # Process request through server
        if self.server_instance:
            status_code, content, content_type, headers = self.server_instance._process_request(
                request, request.client_ip
            )
            self.send_response_data(status_code, content, content_type, headers)
        else:
            self.send_response_data(500, b'Internal Server Error')


class Server:
    """
    Embedded HTTP server for the GLPI Agent.
    
    Listens on the network for messages sent by GLPI servers.
    Supports plugins, SSL, authentication, and multiple listeners.
    """

    def __init__(self, **params):
        """
        Initialize the HTTP server.
        
        Args:
            **params: Server parameters including:
                - logger: Logger instance
                - agent: Agent instance
                - htmldir: Directory for HTML templates and static files
                - ip: Network address to bind (default: all interfaces)
                - port: Network port to listen on (default: 62354)
                - trust: List of trusted IP addresses/ranges
        """
        self.logger = params.get('logger') or Logger()
        self.agent = params.get('agent')
        self.htmldir = params.get('htmldir')
        self.ip = params.get('ip')
        self.port = params.get('port', 62354)
        self.listeners: Dict[int, Dict[str, Any]] = {}
        self.listener: Optional[socket.socket] = None
        self._server: Optional[HTTPServer] = None
        self._servers: Dict[int, HTTPServer] = {}
        self._plugins: List[Any] = []
        self._ssl = None
        self._poller = None
        self._pollers: Dict[int, Any] = {}
        self._timer_event = None
        self._cached_root_content: Optional[bytes] = None
        self._cached_deploy_content: Optional[bytes] = None
        
        # Trust-related attributes
        self.trust: Dict[str, List[Any]] = {}
        self.trusted_cache_trust = None
        self.trusted_cache_expiration = 0
        
        # Initialize trusted addresses cache
        self._handleTrustedAddressesCache(params.get('trust'))
        
        # Load server plugins
        self._load_plugins()

    def _load_plugins(self):
        """Load all server plugin modules."""
        plugins = []
        
        # Find the Server module directory
        module_path = Path(__file__).parent
        
        # Look for plugin files
        plugin_files = glob.glob(str(module_path / "*.py"))
        
        for plugin_file in plugin_files:
            plugin_name = Path(plugin_file).stem
            
            # Skip this file and the Plugin base class
            if plugin_name in ('Server', 'Plugin', '__init__'):
                continue
            
            self.logger.debug(f"{LOG_PREFIX}Trying to load {plugin_name} Server plugin")
            
            try:
                # Dynamically import the plugin module
                module_name = f"GLPI.Agent.HTTP.Server.{plugin_name}"
                module = __import__(module_name, fromlist=[plugin_name])
                
                # Get the plugin class (assume it's named after the module)
                plugin_class = getattr(module, plugin_name, None)
                if not plugin_class:
                    self.logger.debug(
                        f"{LOG_PREFIX}No class {plugin_name} found in module"
                    )
                    continue
                
                # Instantiate the plugin
                plugin = plugin_class(server=self)
                
                if hasattr(plugin, 'init'):
                    plugin.init()
                
                if hasattr(plugin, 'disabled') and plugin.disabled():
                    self.logger.debug(
                        f"{LOG_PREFIX}HTTPD {plugin_name} Server plugin loaded but disabled"
                    )
                else:
                    self.logger.info(
                        f"{LOG_PREFIX}HTTPD {plugin_name} Server plugin loaded"
                    )
                    plugins.append(plugin)
                    
            except Exception as e:
                self.logger.debug(
                    f"{LOG_PREFIX}Failed to load {plugin_name} Server plugin: {e}"
                )
        
        # Sort plugins by priority (highest first)
        if len(plugins) > 1:
            plugins.sort(
                key=lambda p: p.priority() if hasattr(p, 'priority') else 0,
                reverse=True
            )
        
        self._plugins = plugins

    def _handleTrustedAddressesCache(self, trust: Optional[List[str]] = None):
        """
        Handle trusted addresses cache.
        
        Updates the cache of trusted IP addresses and ranges,
        checking expiration and resolving server addresses.
        
        Args:
            trust: List of trusted IP addresses/ranges
        """
        # Initialize trusted cache or check expiration
        if trust is not None:
            self.trusted_cache_trust = trust
        else:
            # Check if cache needs update
            if not self.trusted_cache_trust:
                # Log untrusted addresses
                self._log_untrusted(self.trust)
                self.trust = {}
                return
            
            # Check cache expiration
            if time.time() <= self.trusted_cache_expiration:
                return
            
            trust = self.trusted_cache_trust
        
        # Always reset trust addresses
        delete = self.trust.copy()
        self.trust = {}
        
        # Compute addresses allowed for push requests
        if self.agent and hasattr(self.agent, 'getTargets'):
            for target in self.agent.getTargets():
                if not (hasattr(target, 'isType') and target.isType('server')):
                    continue
                
                url = target.getUrl() if hasattr(target, 'getUrl') else None
                if not url:
                    continue
                
                parsed = urlparse(str(url))
                host = parsed.hostname or parsed.netloc
                
                # Don't resolve server address if still found
                if host in self.trust:
                    delete.pop(host, None)
                    continue
                
                if compile_address is None:
                    continue
                
                addresses = compile_address(host, self.logger)
                if addresses:
                    self.trust[host] = addresses
                    addr_str = ', '.join(str(a) for a in addresses)
                    self.logger.debug(f"Trusted target ip: {addr_str}")
                    delete.pop(host, None)
        
        # Add addresses and ranges defined by httpd-trust option
        if trust:
            for string in trust:
                # Don't resolve if already found
                if string in self.trust:
                    delete.pop(string, None)
                    continue
                
                if compile_address is None:
                    continue
                
                addresses = compile_address(string, self.logger)
                if addresses:
                    self.trust[string] = addresses
                    addr_str = ', '.join(str(a) for a in addresses)
                    self.logger.debug(f"Trusted client ip/range: {addr_str}")
                    delete.pop(string, None)
        
        # Log lost trust
        self._log_untrusted(delete)
        
        # Define cache expiration
        self.trusted_cache_expiration = time.time() + TRUSTED_CACHE_TIMEOUT

    def _log_untrusted(self, delete: Optional[Dict[str, Any]]):
        """
        Log addresses that are no longer trusted.
        
        Args:
            delete: Dictionary of addresses that lost trust
        """
        if not isinstance(delete, dict):
            return
        
        for string in delete.keys():
            self.logger.debug(f"'{string}' client no more trusted")

    def _isTrusted(self, address: str) -> bool:
        """
        Check if an IP address is trusted.
        
        Args:
            address: IP address to check
            
        Returns:
            True if address is trusted, False otherwise
        """
        # Reset trusted cache on expiration
        self._handleTrustedAddressesCache()
        
        if isPartOf is None:
            return False
        
        for trusted_addresses in self.trust.values():
            if isPartOf(address, trusted_addresses, self.logger):
                return True
        
        return False

    def _process_request(self, request: HTTPRequest, client_ip: str) -> Tuple[int, bytes, str, Dict[str, str]]:
        """
        Process HTTP request and return response.
        
        Args:
            request: HTTPRequest object
            client_ip: Client IP address
            
        Returns:
            Tuple of (status_code, content, content_type, headers)
        """
        path = request.path
        headers = {}
        
        # Try plugins first
        for plugin in self._plugins:
            if hasattr(plugin, 'disabled') and plugin.disabled():
                continue
            
            if hasattr(plugin, 'handle'):
                try:
                    result = plugin.handle(request, client_ip)
                    if result is not None:
                        status_code, content, content_type = result if isinstance(result, tuple) else (result, b'', 'text/html')
                        return (status_code, content if isinstance(content, bytes) else str(content).encode('utf-8'), 
                               content_type or 'text/html', headers)
                except Exception as e:
                    self.logger.debug(f"{LOG_PREFIX}Plugin {plugin.name() if hasattr(plugin, 'name') else 'unknown'} error: {e}")
                    continue
        
        # Handle standard paths
        if path == '/' or path == '':
            status_code = self._handle_root(request, client_ip)
            if status_code == 200 and self._cached_root_content:
                return (200, self._cached_root_content, 'text/html', headers)
            return (status_code, self._get_error_message(status_code), 'text/html', headers)
        
        elif path.startswith('/deploy/'):
            sha512 = path[8:]  # Remove '/deploy/' prefix
            status_code = self._handle_deploy(request, client_ip, sha512)
            if status_code == 200 and self._cached_deploy_content:
                # Determine content type from file extension
                content_type = 'application/octet-stream'
                if sha512.endswith(('.json', '.xml', '.txt')):
                    content_type = 'text/plain'
                elif sha512.endswith('.html'):
                    content_type = 'text/html'
                return (200, self._cached_deploy_content, content_type, headers)
            return (status_code, self._get_error_message(status_code), 'text/html', headers)
        
        elif path == '/now':
            status_code = self._handle_now(request, client_ip)
            message = b'OK' if status_code == 200 else b'Access denied'
            return (status_code, message, 'text/plain', headers)
        
        elif path == '/status':
            status_code = self._handle_status(request, client_ip)
            status_text = self.agent.getStatus() if self.agent and hasattr(self.agent, 'getStatus') else 'unknown'
            return (status_code, status_text.encode('utf-8'), 'text/plain', headers)
        
        else:
            return (404, self._get_error_message(404), 'text/html', headers)
    
    def _get_error_message(self, status_code: int) -> bytes:
        """Get error message for status code"""
        messages = {
            400: b'Bad Request',
            403: b'Forbidden',
            404: b'Not Found',
            500: b'Internal Server Error',
            501: b'Not Implemented',
        }
        return messages.get(status_code, b'Error')

    def _handle_root(self, request: HTTPRequest, client_ip: str) -> int:
        """
        Handle root path request (/).
        
        Args:
            request: HTTPRequest object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        if not self.htmldir or not Template:
            return 500
        
        try:
            template_path = Path(self.htmldir) / 'index.tpl'
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            template = Template(template_content)
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX}Template access failed: {e}")
            return 500
        
        trust = self._isTrusted(client_ip)
        
        # Build template context
        context = {
            'version': Version.VERSION,
            'trust': trust,
            'status': self.agent.getStatus() if self.agent else 'unknown',
            'httpd_plugins': [],
            'plugins_url': {},
            'server_targets': [],
            'local_targets': [],
            'sessions': [],
            'planned_tasks': {},
        }
        
        # Get targets if trusted
        if self.agent and hasattr(self.agent, 'getTargets'):
            for target in self.agent.getTargets():
                target_info = {
                    'id': target.id() if hasattr(target, 'id') else '',
                    'date': (target.getFormatedNextRunDate() 
                            if hasattr(target, 'getFormatedNextRunDate') else ''),
                }
                
                if hasattr(target, 'isType'):
                    if target.isType('server'):
                        target_info['target'] = (target.getUrl() 
                                                if trust and hasattr(target, 'getUrl') 
                                                else '')
                        context['server_targets'].append(target_info)
                    elif target.isType('local'):
                        target_info['target'] = (target.getFullPath() 
                                                if trust and hasattr(target, 'getFullPath') 
                                                else '')
                        context['local_targets'].append(target_info)
        
        # Render template and send response
        try:
            html_content = template.render(**context)
            # Store rendered content for response
            self._cached_root_content = html_content.encode('utf-8')
            return 200
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX}Template rendering failed: {e}")
            return 500

    def _handle_deploy(self, request: HTTPRequest, client_ip: str, 
                      sha512: str) -> int:
        """
        Handle deploy file request.
        
        Args:
            request: HTTPRequest object
            client_ip: Client IP address
            sha512: SHA512 hash of requested file
            
        Returns:
            HTTP status code
        """
        # Parse SHA512 to get file path (first char, second char, next 6 chars)
        if len(sha512) < 8:
            return 404
        
        match = re.match(r'^(.)(.)(.{6})', sha512)
        if not match:
            return 404
        
        sub_file_path = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        
        try:
            import hashlib
        except ImportError:
            self.logger.error("Failed to load hashlib")
            return 501
        
        path = None
        count = 0
        
        # Search for file in deploy directories
        if self.agent and hasattr(self.agent, 'getTargets'):
            for target in self.agent.getTargets():
                if not hasattr(target, 'storage'):
                    continue
                
                storage_dir = target.storage.getDirectory()
                pattern = f"{storage_dir}/deploy/fileparts/shared/*"
                
                for shared_dir in glob.glob(pattern):
                    file_path = os.path.join(shared_dir, sub_file_path)
                    
                    if not os.path.isfile(file_path):
                        continue
                    
                    count += 1
                    
                    # Verify SHA512 hash
                    sha = hashlib.sha512()
                    with open(file_path, 'rb') as f:
                        sha.update(f.read())
                    
                    if sha.hexdigest() == sha512:
                        path = file_path
                        break
                
                if path:
                    break
        
        if path:
            # Store file path for response
            try:
                with open(path, 'rb') as f:
                    self._cached_deploy_content = f.read()
                return 200
            except Exception as e:
                self.logger.error(f"{LOG_PREFIX}Error reading deploy file: {e}")
                return 500
        else:
            return 404

    def _handle_now(self, request: HTTPRequest, client_ip: str) -> int:
        """
        Handle /now request to trigger immediate run.
        
        Args:
            request: HTTPRequest object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        code = 200
        message = "OK"
        trace = None
        
        # Check if request is from trusted source
        targets = []
        
        if self.agent and hasattr(self.agent, 'getTargets'):
            for target in self.agent.getTargets():
                if not (hasattr(target, 'isType') and target.isType('server')):
                    continue
                
                url = target.getUrl() if hasattr(target, 'getUrl') else None
                if not url:
                    continue
                
                addresses = self.trust.get(str(url))
                if addresses and isPartOf and isPartOf(client_ip, addresses, self.logger):
                    trace = f"rescheduling next contact for target {url} right now"
                    targets.append(target)
                    break
        
        # If not found in server targets, check if generally trusted
        if not targets and self._isTrusted(client_ip):
            if self.agent and hasattr(self.agent, 'getTargets'):
                targets = list(self.agent.getTargets())
        
        if targets:
            # Reschedule next contact for targets
            for target in targets:
                if hasattr(target, 'setNextRunDate'):
                    target.setNextRunDate(time.time())
            trace = "rescheduling next contact for all targets right now"
        else:
            code = 403
            message = "Access denied"
            trace = "invalid request (untrusted address)"
        
        if trace:
            self.logger.debug(f"{LOG_PREFIX}{trace}")
        
        return code

    def _handle_status(self, request: HTTPRequest, client_ip: str) -> int:
        """
        Handle /status request.
        
        Args:
            request: HTTPRequest object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        # Status will be returned in response content
        return 200

    def init(self) -> bool:
        """
        Initialize and start the HTTP server listener.
        
        Returns:
            True on success, False on failure
        """
        try:
            # Create HTTP request handler factory
            def handler_factory(*args, **kwargs):
                return HTTPRequestHandler(*args, server=self, **kwargs)
            
            # Create main HTTP server
            bind_ip = self.ip if self.ip else ''
            try:
                self._server = HTTPServer((bind_ip, self.port), handler_factory)
                self._server.timeout = 1.0  # Non-blocking timeout
                self.listener = self._server.socket
                
                self.logger.info(
                    f"{LOG_PREFIX}HTTPD service started on {bind_ip or 'all interfaces'}:{self.port}"
                )
            except OSError as e:
                self.logger.error(f"{LOG_PREFIX}Failed to bind to {bind_ip}:{self.port}: {e}")
                return False
            
            # Initialize plugins and set up additional listeners
            plugins = {}
            for plugin in self._plugins:
                plugins[plugin.name() if hasattr(plugin, 'name') else str(plugin)] = plugin
            
            # Handle SSL and port-specific plugins
            for plugin in self._plugins:
                if hasattr(plugin, 'disabled') and plugin.disabled():
                    continue
                
                # Special handling for SSL plugin
                if hasattr(plugin, 'name') and plugin.name() == 'SSL':
                    if hasattr(plugin, 'config'):
                        ports = plugin.config('ports') or []
                        for port in ports:
                            if not port or port == self.port:
                                self._ssl = plugin
                                self.logger.info(
                                    f"{LOG_PREFIX}HTTPD SSL Server plugin enabled on default port"
                                )
                            else:
                                # Create listener for SSL on different port
                                self.logger.info(
                                    f"{LOG_PREFIX}HTTPD SSL Server plugin enabled on port {port}"
                                )
                    
                    if hasattr(plugin, 'name'):
                        plugins.pop(plugin.name(), None)
                    continue
                
                # Handle plugins with dedicated ports
                if hasattr(plugin, 'port'):
                    port = plugin.port()
                    if port and port != self.port:
                        if port not in self.listeners:
                            try:
                                # Create additional HTTP server for this port
                                additional_server = HTTPServer((bind_ip, port), handler_factory)
                                additional_server.timeout = 1.0
                                self._servers[port] = additional_server
                                
                                self.listeners[port] = {
                                    'listener': additional_server.socket,
                                    'plugins': [plugin],
                                }
                                self.logger.info(
                                    f"{LOG_PREFIX}HTTPD {plugin.name() if hasattr(plugin, 'name') else 'plugin'} Server plugin started on port {port}"
                                )
                            except OSError as e:
                                self.logger.error(f"{LOG_PREFIX}Failed to start plugin on port {port}: {e}")
                        else:
                            self.listeners[port]['plugins'].append(plugin)
                        
                        if hasattr(plugin, 'name'):
                            plugins.pop(plugin.name(), None)
            
            self._plugins = list(plugins.values())
            
            return True
            
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX}failed to start the HTTPD service: {e}")
            return False

    def plugins_list(self) -> Dict[str, Any]:
        """
        Get a list of all loaded plugins and their configurations.
        
        Returns:
            Dictionary mapping plugin names to their configurations
        """
        plugins = list(self._plugins)
        
        # Add plugins from additional listeners
        if self.listeners:
            for listener_info in self.listeners.values():
                if 'plugins' in listener_info:
                    plugins.extend(listener_info['plugins'])
                if 'ssl' in listener_info and listener_info['ssl']:
                    plugins.append(listener_info['ssl'])
        
        result = {}
        for plugin in plugins:
            name = plugin.name().lower() if hasattr(plugin, 'name') else 'unknown'
            
            if hasattr(plugin, 'disabled') and plugin.disabled():
                result[name] = "disabled"
            else:
                config = {}
                if hasattr(plugin, 'defaults') and hasattr(plugin, 'config'):
                    defaults = plugin.defaults()
                    if isinstance(defaults, dict):
                        for key in defaults.keys():
                            config[key] = plugin.config(key)
                result[name] = config
        
        return result

    def needToRestart(self, **params) -> bool:
        """
        Check if server needs to restart due to configuration changes.
        
        Args:
            **params: New configuration parameters
            
        Returns:
            True if restart is needed, False otherwise
        """
        # If no httpd daemon was started, we need to start it
        if not self.listener:
            return True
        
        # Restart if IP or port changed
        if params.get('ip') and (not self.ip or params['ip'] != self.ip):
            return True
        if params.get('port') and (not self.port or params['port'] != self.port):
            return True
        
        # Check if any plugin configuration changed
        for plugin in self._plugins:
            old_port = plugin.port() if hasattr(plugin, 'port') else None
            old_disabled = plugin.disabled() if hasattr(plugin, 'disabled') else False
            
            if hasattr(plugin, 'init'):
                plugin.init()
            
            new_port = plugin.port() if hasattr(plugin, 'port') else None
            new_disabled = plugin.disabled() if hasattr(plugin, 'disabled') else False
            
            if old_port != new_port or old_disabled != new_disabled:
                return True
        
        # Update logger if provided
        if 'logger' in params:
            self.logger = params['logger']
            self.logger.debug2(
                f"{LOG_PREFIX}HTTPD service still listening on port {self.port}"
            )
        
        # Reset trusted addresses
        self.trusted_cache_trust = None
        self._handleTrustedAddressesCache(params.get('trust'))
        
        return False

    def stop(self):
        """Stop the HTTP server and all listeners."""
        if not self.listener:
            return
        
        # Stop additional listeners
        for port, listener_info in list(self.listeners.items()):
            if port in self._servers:
                try:
                    self._servers[port].shutdown()
                    self._servers[port].server_close()
                except Exception:
                    pass
                del self._servers[port]
        
        self.listeners = {}
        
        # Stop main listener
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
        
        self.listener = None
        
        self.logger.debug(f"{LOG_PREFIX}HTTPD service stopped")
        
        self._plugins = []

    def handleRequests(self) -> int:
        """
        Check for and handle incoming HTTP requests.
        
        Returns:
            Number of connections handled
        """
        if not self.listener:
            return 0
        
        # Handle timer events on plugins
        if not self._timer_event or self._timer_event <= time.time():
            enabled_plugins = [
                p for p in self._plugins 
                if not (hasattr(p, 'disabled') and p.disabled())
            ]
            
            timeouts = []
            for plugin in enabled_plugins:
                if hasattr(plugin, 'timer_event'):
                    timeout = plugin.timer_event()
                    if timeout:
                        timeouts.append(timeout)
            
            if timeouts:
                self._timer_event = min(timeouts)
            else:
                self._timer_event = time.time() + 60
        
        # Handle requests using select() for non-blocking I/O
        got_connection = 0
        
        # Collect all listening sockets
        sockets = []
        if self.listener:
            sockets.append(self.listener)
        
        for listener_info in self.listeners.values():
            if 'listener' in listener_info and listener_info['listener']:
                sockets.append(listener_info['listener'])
        
        if not sockets:
            return 0
        
        # Use select to check for ready sockets (non-blocking)
        try:
            ready_sockets, _, _ = select.select(sockets, [], [], 0.1)
        except (OSError, ValueError):
            # Socket may have been closed
            return 0
        
        # Handle requests on ready sockets
        for sock in ready_sockets:
            try:
                # Handle main server
                if sock == self.listener and self._server:
                    self._server.handle_request()
                    got_connection += 1
                # Handle additional servers
                else:
                    for port, server in self._servers.items():
                        if sock == server.socket:
                            server.handle_request()
                            got_connection += 1
                            break
            except Exception as e:
                self.logger.debug(f"{LOG_PREFIX}Error handling request: {e}")
        
        return got_connection

