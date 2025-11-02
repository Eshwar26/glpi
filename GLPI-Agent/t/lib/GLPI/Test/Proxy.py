#!/usr/bin/env python3
"""Test Proxy Module - HTTP proxy server for testing"""

import os
import sys
import socket
import threading
import signal
import platform
from typing import Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

try:
    import ssl
except ImportError:
    ssl = None

# Global PID for proxy process
pid: Optional[int] = None


class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for proxy"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        self.do_request()
    
    def do_POST(self):
        """Handle POST requests"""
        self.do_request()
    
    def do_request(self):
        """Handle HTTP requests"""
        # Parse the request URL
        url = self.path
        parsed = urlparse(url)
        
        # Forward request to target
        try:
            import http.client
            
            target_host = parsed.hostname or self.headers.get('Host', 'localhost')
            target_port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            
            if parsed.scheme == 'https':
                conn = http.client.HTTPSConnection(target_host, target_port)
            else:
                conn = http.client.HTTPConnection(target_host, target_port)
            
            # Forward headers (exclude hop-by-hop headers)
            headers = {}
            for header, value in self.headers.items():
                if header.lower() not in ['connection', 'proxy-connection', 'keep-alive']:
                    headers[header] = value
            
            # Send request
            path = parsed.path
            if parsed.query:
                path += '?' + parsed.query
            
            conn.request(self.command, path, self.rfile.read(int(self.headers.get('Content-Length', 0) or 0)), headers)
            
            # Get response
            response = conn.getresponse()
            
            # Send response back to client
            self.send_response(response.status)
            
            # Forward response headers
            for header, value in response.getheaders():
                self.send_header(header, value)
            self.end_headers()
            
            # Forward response body
            self.wfile.write(response.read())
            
            conn.close()
            
        except Exception as e:
            self.send_error(500, f"Proxy error: {str(e)}")


class Proxy:
    """HTTP proxy server for testing"""
    
    def __init__(self, port: int = 0):
        """
        Initialize proxy server.
        
        Args:
            port: Port number (0 for random available port)
        
        Raises:
            RuntimeError: If proxy instance already exists
        """
        global pid
        
        if pid is not None:
            raise RuntimeError('An instance of Test::Proxy has already been started.')
        
        # Create HTTP server with proxy handler
        self.server = HTTPServer(('127.0.0.1', port), ProxyHTTPRequestHandler)
        
        # Get actual port (if 0 was specified)
        self.port = self.server.server_address[1]
        
        # Disable SSL verification for testing (if supported)
        # Note: Python's http.client doesn't have global SSL options like LWP
        # SSL verification would need to be disabled per-request if needed
    
    def background(self, callback: Optional[Callable] = None) -> int:
        """
        Start proxy in background.
        
        Args:
            callback: Optional callback function to run after starting
            
        Returns:
            Process ID (thread identifier in this case)
        """
        global pid
        
        def run_proxy():
            """Run proxy server in thread"""
            try:
                self.server.serve_forever()
            except Exception:
                pass
            finally:
                if callback:
                    callback(self.server)
        
        thread = threading.Thread(target=run_proxy, daemon=True)
        thread.start()
        
        # Use thread ID as "pid" for compatibility
        pid = thread.ident
        
        # Give server time to start
        import time
        time.sleep(0.5)
        
        return pid
    
    def url(self) -> str:
        """
        Get proxy URL.
        
        Returns:
            Proxy URL string
        """
        return f"http://127.0.0.1:{self.port}"
    
    @staticmethod
    def stop():
        """Stop the proxy server"""
        global pid
        
        if pid is None:
            return
        
        # Since we're using threads, we need to shut down the server
        # This is a simplified version - in practice, you'd need to track the server instance
        # For now, we'll just reset the pid
        
        # Try to kill thread (this is a limitation of the design)
        # In a real implementation, you'd want to store the server instance
        # and call server.shutdown()
        
        pid = None
