#!/usr/bin/env python3
"""Test Server Module - HTTP server for testing"""

import os
import sys
import socket
import threading
import base64
import platform
from pathlib import Path
from typing import Optional, Dict, Callable, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    import ssl
except ImportError:
    ssl = None

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'lib'))

try:
    from GLPI.Test.Auth import Auth
except ImportError:
    # Fallback Auth class
    class Auth:
        def __init__(self, user, password):
            self.user = user
            self.password = password
        def check(self, user, password):
            return user == self.user and password == self.password
        def check_auth_header(self, auth_header):
            if not auth_header or not auth_header.startswith('Basic '):
                return False
            try:
                encoded = auth_header[6:]
                decoded = base64.b64decode(encoded).decode('utf-8')
                u, p = decoded.split(':', 1)
                return self.check(u, p)
            except:
                return False

# Global dispatch table and PID
_dispatch_table: Dict[str, Any] = {}
pid: Optional[int] = None
_server_instance: Optional['TestServer'] = None


class CGIEnvironment:
    """CGI-like environment wrapper"""
    
    def __init__(self, handler: BaseHTTPRequestHandler):
        """Initialize with HTTP request handler"""
        self.handler = handler
        self._path_info = handler.path.split('?')[0]
        
        # Parse query string
        parsed = urlparse(handler.path)
        self.query_string = parsed.query
        self.query_params = parse_qs(self.query_string)
    
    def path_info(self) -> str:
        """Get PATH_INFO"""
        return self._path_info
    
    def header(self, **kwargs) -> str:
        """Generate HTTP header"""
        return ""
    
    def start_html(self, title: str = "") -> str:
        """Generate HTML start"""
        return f"<html><head><title>{title}</title></head><body>"
    
    def h1(self, text: str) -> str:
        """Generate H1 tag"""
        return f"<h1>{text}</h1>"
    
    def end_html(self) -> str:
        """Generate HTML end"""
        return "</body></html>"


class TestHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for test server"""
    
    def __init__(self, *args, server=None, **kwargs):
        """Initialize with server reference"""
        self.test_server = server
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        self.handle_request()
    
    def do_POST(self):
        """Handle POST requests"""
        self.handle_request()
    
    def handle_request(self):
        """Handle HTTP request"""
        # Check authentication if required
        if self.test_server.user or self.test_server.password:
            auth_header = self.headers.get('Authorization')
            if not self.test_server.auth_handler.check_auth_header(auth_header):
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Test Server"')
                self.end_headers()
                self.wfile.write(b'Authentication required.')
                return
        
        # Create CGI-like environment
        cgi = CGIEnvironment(self)
        path = cgi.path_info()
        
        # Look up handler in dispatch table
        handler = _dispatch_table.get(path)
        
        if handler:
            if callable(handler):
                # Call handler function
                handler(self.test_server, cgi)
            else:
                # Return static content
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                if isinstance(handler, bytes):
                    self.wfile.write(handler)
                else:
                    self.wfile.write(handler.encode('utf-8'))
        else:
            # 404 Not found
            self.send_response(404)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = cgi.start_html('Not found') + cgi.h1('Not found') + cgi.end_html()
            self.wfile.write(html.encode('utf-8'))
        
        # Fix for CONTENT_LENGTH environment variable
        if 'CONTENT_LENGTH' in os.environ:
            del os.environ['CONTENT_LENGTH']


class TestServer:
    """HTTP test server"""
    
    def __init__(self, port: int = 8080, ssl: bool = False, 
                 crt: Optional[str] = None, key: Optional[str] = None,
                 user: Optional[str] = None, password: Optional[str] = None,
                 host: str = '127.0.0.1'):
        """
        Initialize test server.
        
        Args:
            port: Port number (default: 8080)
            ssl: Enable SSL/TLS
            crt: Path to SSL certificate file
            key: Path to SSL private key file
            user: Username for basic authentication
            password: Password for basic authentication
            host: Host address (default: 127.0.0.1)
        
        Raises:
            RuntimeError: If server instance already exists
        """
        global pid, _server_instance
        
        if pid is not None or _server_instance is not None:
            raise RuntimeError('An instance of Test::Server has already been started.')
        
        self.port = port
        self.host = host
        self.user = user
        self.password = password
        self.ssl_enabled = ssl
        self.crt = crt
        self.key = key
        
        # Create authentication handler
        self.auth_handler = Auth(user or '', password or '')
        
        # Create HTTP server
        def handler_factory(*args, **kwargs):
            return TestHTTPRequestHandler(*args, server=self, **kwargs)
        
        self.server = HTTPServer((host, port), handler_factory)
        
        # Setup SSL if enabled
        if ssl and ssl is not None:
            if not self.crt or not self.key:
                raise ValueError("SSL certificate and key files required for SSL")
            
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.crt, self.key)
            self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        
        _server_instance = self
    
    def set_dispatch(self, dispatch_table: Dict[str, Any]):
        """
        Set dispatch table for request routing.
        
        Args:
            dispatch_table: Dictionary mapping paths to handlers or content
        """
        global _dispatch_table
        _dispatch_table = dispatch_table
    
    def background(self) -> int:
        """
        Start server in background.
        
        Returns:
            Thread identifier
        """
        global pid
        
        def run_server():
            """Run server in thread"""
            try:
                self.server.serve_forever()
            except Exception:
                pass
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        # Use thread ID as "pid"
        pid = thread.ident
        
        # Give server time to start
        import time
        time.sleep(1)
        
        return pid
    
    def root(self) -> str:
        """
        Get server root URL.
        
        Returns:
            Server URL string
        """
        protocol = 'https' if self.ssl_enabled else 'http'
        return f"{protocol}://{self.host}:{self.port}"
    
    @staticmethod
    def stop():
        """Stop the server"""
        global pid, _server_instance
        
        if _server_instance:
            try:
                _server_instance.server.shutdown()
                _server_instance.server.server_close()
            except:
                pass
            _server_instance = None
        
        pid = None


# For backward compatibility, allow creating instance directly
def create_server(**kwargs) -> TestServer:
    """Create a new test server instance"""
    return TestServer(**kwargs)
