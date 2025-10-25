"""
GLPI Agent HTTP Server ToolBox Credentials Module

Manages credentials for network discovery and inventory tasks.
"""

from typing import Dict, Any
from html import escape

try:
    from GLPI.Agent.HTTP.Server.ToolBox import ToolBox
except ImportError:
    ToolBox = object


class Credentials(ToolBox if ToolBox != object else object):
    """
    Credentials page for ToolBox interface.
    
    Manages SNMP, SSH, and other credentials for network tasks.
    """

    CREDENTIALS = "credentials"

    def __init__(self, **params):
        """Initialize Credentials page."""
        self.toolbox = params.get('toolbox')
        self.logger = None
        self.name = "Credentials"
        
        if self.toolbox:
            self.logger = getattr(self.toolbox, 'logger', None)

    def index(self) -> str:
        """Get the page index/path."""
        return self.CREDENTIALS

    def log_prefix(self) -> str:
        """Get the log prefix for this page."""
        return "[toolbox plugin, credentials] "

    def yaml_config_specs(self, yaml_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get YAML configuration specifications.
        
        Args:
            yaml_config: Current YAML configuration
            
        Returns:
            Dictionary of configuration specs
        """
        if not self.toolbox:
            return {}
        
        is_updating = self.toolbox.isyes(yaml_config.get('updating_support'))
        
        return {
            'credentials_navbar': {
                'category': "Navigation bar",
                'type': "bool" if is_updating else "readonly",
                'value': self.toolbox.yesno(yaml_config.get('credentials_navbar')),
                'text': "Show Credentials in navigation bar",
                'navbar': "Credentials",
                'link': self.index(),
                'icon': "key",
                'index': 50,
            },
            'credentials_yaml': {
                'category': "Toolbox plugin configuration",
                'type': "option" if is_updating else "readonly",
                'value': yaml_config.get('credentials_yaml') or (
                    "" if is_updating else "[default]"
                ),
                'options': self.toolbox.yaml_files() if hasattr(self.toolbox, 'yaml_files') else [],
                'text': "Credentials YAML file",
                'yaml_base': self.CREDENTIALS,
            }
        }

    def update_template_hash(self, hash_data: Dict[str, Any]):
        """
        Update template hash for rendering.
        
        Args:
            hash_data: Template hash to update
        """
        if not hash_data or not self.toolbox:
            return
        
        yaml_data = self.toolbox.yaml() or {}
        credentials = yaml_data.get(self.CREDENTIALS, {})
        
        # Update template hash
        hash_data[self.CREDENTIALS] = {}
        
        for name, entry in credentials.items():
            hash_data[self.CREDENTIALS][name] = {}
            for key, value in entry.items():
                if value is not None:
                    # Escape sensitive fields
                    if key in ('name', 'description', 'username', 
                             'authpassword', 'privpassword'):
                        value = escape(str(value))
                    hash_data[self.CREDENTIALS][name][key] = value
        
        hash_data['title'] = "Credentials"

    def need_init(self) -> bool:
        """Check if page needs initialization."""
        return False

    def handle_form(self, form: Dict[str, Any]):
        """
        Handle form submission.
        
        Args:
            form: Form data dictionary
        """
        pass

