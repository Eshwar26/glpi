"""
GLPI Agent HTTP Server ToolBox Plugin

Provides a web-based toolbox interface for agent management and configuration.
Supports dynamic pages, YAML configuration, and session management.
"""

import os
import re
import time
import glob
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from urllib.parse import unquote
from html import escape, unescape

from GLPI.Agent.HTTP.Server.Plugin import Plugin

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    try:
        from ruamel import yaml
        YAML_AVAILABLE = True
    except ImportError:
        YAML_AVAILABLE = False

try:
    from GLPI.Agent.Target.Listener import Listener
except ImportError:
    Listener = None


VERSION = "1.6"


class ToolBox(Plugin):
    """
    ToolBox server plugin for web-based agent management.
    
    Provides:
    - Configuration management
    - Inventory results viewing
    - Network discovery/inventory tools
    - Credentials management
    - YAML configuration editing
    """

    def __init__(self, **params):
        """Initialize ToolBox plugin."""
        super().__init__(**params)
        
        # API endpoint mappings
        self.api_match = {
            'version': self._version,
            'toolbox': self._index,
            'configuration': self._index,
            'yaml': self._index,
            'credentials': self._index,
            'toolbox.css': self._file,
            'configuration.css': self._file,
            'inventory.css': self._file,
            'results.css': self._file,
            'custom.css': self._file,
            'mibsupport.css': self._file,
            'logo.png': self._logo,
            'favicon.ico': self._favicon,
        }

    def urlMatch(self, path: str) -> bool:
        """
        Check if URL path matches ToolBox endpoints.
        
        Args:
            path: URL path to check
            
        Returns:
            True if path matches, False otherwise
        """
        if not path:
            return False
        
        # Handle index page
        re_index_match = getattr(self, 're_index_match', None)
        if re_index_match and re_index_match.match(path):
            self.request = 'toolbox'
            return True
        
        # Handle files to send after redirect
        send_file = getattr(self, '_send_file', {})
        if path in send_file:
            self.request = path
            self.api_match[path] = self._send_file_handler
            return True
        
        # Handle main API paths
        re_path_match = getattr(self, 're_path_match', None)
        if re_path_match:
            match = re_path_match.match(path)
            if match:
                self.request = match.group(1)
                return True
        
        # Handle favicon
        if path == '/favicon.ico':
            self.request = 'favicon.ico'
            return True
        
        return False

    def init(self):
        """Initialize the ToolBox plugin."""
        super().init()
        
        # Don't do more initialization if disabled
        if self.disabled():
            return
        
        self.request = 'home'
        self._pages = {}
        self._ajax = {}
        self._send_file = {}
        
        # Load ToolBox page modules
        self._load_pages()
        
        # Setup URL patterns
        defaults = self.defaults()
        self.index = self.config('url_path')
        
        if self.index != defaults['url_path']:
            self.debug(f"Using {self.index} as base url matching")
        
        # Build regex for API endpoints
        regexp_api_match = '|'.join(self.api_match.keys())
        self.re_path_match = re.compile(f"^{self.index}/({regexp_api_match})$")
        self.re_index_match = re.compile(f"^{self.index}/?$")
        
        self.htmldir = getattr(self.server, 'htmldir', '') if self.server else ''
        
        # Normalize configurations
        raw_edition = self.config('raw_edition')
        self.config('raw_edition', self.yesno(raw_edition))
        
        # Normalize header color
        if self.config('headercolor'):
            if not re.match(r'^[0-9a-fA-F]{6}$', str(self.config('headercolor'))):
                self.debug("Wrong headercolor found")
                self.config('headercolor', None)
            else:
                self.config('headercolor', '#' + self.config('headercolor'))
        
        # Setup Listener target
        if Listener and self.server and hasattr(self.server, 'agent'):
            agent = self.server.agent
            vardir = getattr(agent.config, 'vardir', None) if hasattr(agent, 'config') else None
            
            self.target = Listener(
                logger=self.logger,
                basevardir=vardir,
            )
        
        # Handle YAML configuration
        if YAML_AVAILABLE:
            self._setup_yaml()
        else:
            self.info("Can't handle ToolBox online configuration without YAML support")
        
        # Initialize pages that need it
        for page in self._pages.values():
            if hasattr(page, 'need_init') and page.need_init():
                if hasattr(page, 'init'):
                    page.init()
        
        # Update Results page if available
        if hasattr(self, '_results') and self._results:
            if hasattr(self._results, 'xml_analysis'):
                self._results.xml_analysis()
        
        self._errors = []
        self._infos = []
        self._yaml = {}
        
        # Initialize session timeout
        yaml_data = self.yaml() or {}
        yaml_config = yaml_data.get('configuration', {})
        self._session_timeout = yaml_config.get('session_timeout', 86400)

    def _load_pages(self):
        """Load all ToolBox page modules."""
        # Find ToolBox page modules
        module_file = Path(__file__)
        pages_path = module_file.parent
        
        for file_path in glob.glob(str(pages_path / "*.py")):
            name = Path(file_path).stem
            
            # Skip __init__ and this file
            if name in ('ToolBox', 'Plugin', '__init__'):
                continue
            
            self.debug2(f"Trying to load {name} ToolBox module")
            
            try:
                # Dynamically import the module
                module_name = f"GLPI.Agent.HTTP.Server.{name}"
                module = __import__(module_name, fromlist=[name])
                
                # Get the class
                page_class = getattr(module, name, None)
                if not page_class:
                    continue
                
                # Instantiate the page
                page = page_class(toolbox=self)
                
                if hasattr(page, 'index'):
                    index = page.index()
                    self.api_match[index] = self._index
                    self._pages[index] = page
                    
                    # Register AJAX support
                    if hasattr(page, 'ajax_support') and page.ajax_support():
                        self._ajax[index] = page
                        self.api_match[f"{index}/ajax"] = True
                    
                    # Register events callback
                    if (hasattr(page, 'register_events_cb') and 
                        page.register_events_cb() and
                        self.server and hasattr(self.server, 'agent')):
                        agent = self.server.agent
                        if hasattr(agent, 'register_events_cb'):
                            agent.register_events_cb(page)
                    
                    # Keep Results page reference
                    if name == 'Results':
                        self._results = page
                        
            except Exception as e:
                self.logger.debug(f"Failed to load {name} ToolBox page: {e}")

    def _setup_yaml(self):
        """Setup YAML configuration handling."""
        yaml_file = self.config('yaml')
        self.yamlconfig = yaml_file
        
        confdir = self.confdir()
        if confdir:
            yaml_path = os.path.join(confdir, yaml_file)
            if not os.path.exists(yaml_path):
                # Create default YAML
                default_yaml = {
                    'configuration': {
                        'updating_support': 'yes'
                    }
                }
                
                self.debug(f"Saving default {yaml_file} file")
                self.debug(f"YAML file: {yaml_path}")
                
                try:
                    with open(yaml_path, 'w') as f:
                        yaml.dump(default_yaml, f)
                    self.yamlconfig = yaml_path
                    self._yaml = default_yaml
                except Exception as e:
                    self.error(f"Failed to create YAML file: {e}")
            else:
                self.yamlconfig = yaml_path
        
        # Scan for YAML files in confdir
        self.scan_yaml_files()

    def handle(self, client, request, client_ip: str) -> int:
        """
        Handle ToolBox request.
        
        Args:
            client: Client connection
            request: HTTP request object
            client_ip: Client IP address
            
        Returns:
            HTTP status code
        """
        request_type = getattr(self, 'request', None)
        
        if not request_type or request_type not in self.api_match:
            self.info(f"unsupported api request from {client_ip}")
            if hasattr(client, 'send_error'):
                client.send_error(404)
            return 404
        
        # Handle AJAX requests
        ajax_match = re.match(r'^(.*)/ajax$', request_type)
        if ajax_match:
            ajax_page = ajax_match.group(1)
            if ajax_page in self._ajax:
                # Handle AJAX (simplified)
                pass
            
            self.info(f"unsupported ajax request from {client_ip}")
            if hasattr(client, 'send_error'):
                client.send_error(404)
            return 404
        
        # Call the appropriate handler
        handler = self.api_match.get(request_type)
        if callable(handler):
            return handler(client, request, client_ip)
        
        return 404

    def log_prefix(self) -> str:
        """Get the log prefix for this plugin."""
        return "[toolbox plugin] "

    def config_file(self) -> str:
        """Get the configuration filename."""
        return "toolbox-plugin.cfg"

    def defaults(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of defaults
        """
        return {
            'disabled': "yes",
            'url_path': "/toolbox",
            'port': 0,
            'yaml': "toolbox.yaml",
            'logo': "toolbox/logo.png",
            'addnavlink': None,
            'headercolor': None,
            'raw_edition': "no",
            'forbid_not_trusted': "no",
        }

    def supported_method(self, method: str) -> bool:
        """Check if request method is supported."""
        if method in ('GET', 'POST'):
            return True
        
        self.error(f"invalid request type: {method}")
        return False

    def yesno(self, value: Any) -> str:
        """
        Convert value to yes/no string.
        
        Args:
            value: Value to convert
            
        Returns:
            "yes" or "no"
        """
        if value and re.match(r'^1|yes|true$', str(value), re.IGNORECASE):
            return "yes"
        return "no"

    def isyes(self, value: Any) -> bool:
        """
        Check if value is affirmative.
        
        Args:
            value: Value to check
            
        Returns:
            True if yes/true/1
        """
        if value and re.match(r'^1|yes|true$', str(value), re.IGNORECASE):
            return True
        return False

    def yaml(self, data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get or set YAML configuration.
        
        Args:
            data: Optional YAML data to set
            
        Returns:
            YAML configuration dictionary
        """
        if data is not None:
            if isinstance(data, dict):
                if not self._yaml:
                    self._yaml = {}
                self._yaml.update(data)
        
        return self._yaml

    def scan_yaml_files(self):
        """Scan configuration directory for YAML files."""
        self._scanned_yamls = [self.config('yaml')]
        
        confdir = self.confdir()
        if confdir:
            for pattern in ['*.yaml', '*.yml']:
                for file_path in glob.glob(os.path.join(confdir, pattern)):
                    config_file = os.path.basename(file_path)
                    if config_file != self.config('yaml'):
                        self._scanned_yamls.append(config_file)

    def _version(self, client, request, client_ip: str) -> int:
        """Handle version request."""
        # Send version (simplified)
        if hasattr(client, 'send_response'):
            pass
        return 200

    def _index(self, client, request, client_ip: str) -> int:
        """Handle index/main page request."""
        # This would render the main ToolBox interface (simplified)
        return 200

    def _file(self, client, request=None, client_ip: str = None) -> int:
        """Handle static file request."""
        request_type = getattr(self, 'request', '')
        file_path = os.path.join(self.htmldir, "toolbox", request_type)
        
        if hasattr(client, 'send_file_response') and os.path.exists(file_path):
            client.send_file_response(file_path)
            return 200
        
        return 404

    def _logo(self, client, request=None, client_ip: str = None) -> int:
        """Handle logo request."""
        logo = self.config('logo')
        
        # Try alternative paths if logo not found
        if not logo or not os.path.exists(logo):
            logo = os.path.join(self.htmldir, logo) if logo else None
        
        if not logo or not os.path.exists(logo):
            defaults_logo = self.defaults()['logo']
            logo = os.path.join(self.htmldir, defaults_logo)
        
        if hasattr(client, 'send_file_response') and os.path.exists(logo):
            client.send_file_response(logo)
            return 200
        
        return 404

    def _favicon(self, client, request=None, client_ip: str = None) -> int:
        """Handle favicon request."""
        favicon_path = os.path.join(self.htmldir, "favicon.ico")
        
        if hasattr(client, 'send_file_response') and os.path.exists(favicon_path):
            client.send_file_response(favicon_path)
            return 200
        
        return 404

    def _send_file_handler(self, client, request, client_ip: str) -> int:
        """Handle file send request."""
        file_url = getattr(self, 'request', '')
        file_path = self._send_file.get(file_url)
        
        if not file_path or not os.path.exists(file_path):
            self.error(f"send file failure for {file_url}")
            if hasattr(client, 'send_error'):
                client.send_error(404)
            return 404
        
        if hasattr(client, 'send_file_response'):
            client.send_file_response(file_path)
        
        # Delete the file after sending
        try:
            os.unlink(file_path)
        except:
            pass
        
        return 200

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

