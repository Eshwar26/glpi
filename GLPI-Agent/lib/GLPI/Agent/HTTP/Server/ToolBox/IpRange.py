"""
GLPI Agent HTTP Server ToolBox IP Range Module

Manages IP ranges for network discovery and inventory tasks.
"""

from typing import Dict, Any
from html import escape

try:
    from GLPI.Agent.HTTP.Server.ToolBox import ToolBox
except ImportError:
    ToolBox = object


class IpRange(ToolBox if ToolBox != object else object):
    """
    IP Range page for ToolBox interface.
    
    Manages IP address ranges for network discovery.
    """

    IP_RANGE = "ip_range"

    def __init__(self, **params):
        """Initialize IP Range page."""
        self.toolbox = params.get('toolbox')
        self.logger = None
        self.name = "IpRange"
        
        if self.toolbox:
            self.logger = getattr(self.toolbox, 'logger', None)

    def index(self) -> str:
        """Get the page index/path."""
        return self.IP_RANGE

    def log_prefix(self) -> str:
        """Get the log prefix for this page."""
        return "[toolbox plugin, ip_range] "

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
            'iprange_navbar': {
                'category': "Navigation bar",
                'type': "bool" if is_updating else "readonly",
                'value': self.toolbox.yesno(yaml_config.get('iprange_navbar')),
                'text': "Show IP Ranges in navigation bar",
                'navbar': "IP Ranges",
                'link': self.index(),
                'icon': "network",
                'index': 40,
            },
            'iprange_yaml': {
                'category': "Toolbox plugin configuration",
                'type': "option" if is_updating else "readonly",
                'value': yaml_config.get('iprange_yaml') or (
                    "" if is_updating else "[default]"
                ),
                'options': self.toolbox.yaml_files() if hasattr(self.toolbox, 'yaml_files') else [],
                'text': "IP Ranges YAML file",
                'yaml_base': self.IP_RANGE,
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
        ip_range = yaml_data.get(self.IP_RANGE, {})
        
        # Update template hash
        hash_data[self.IP_RANGE] = {}
        
        for name, entry in ip_range.items():
            hash_data[self.IP_RANGE][name] = {}
            for key, value in entry.items():
                if value is not None:
                    # Escape certain fields
                    if key in ('name', 'description'):
                        value = escape(str(value))
                    hash_data[self.IP_RANGE][name][key] = value
        
        hash_data['title'] = "IP Ranges"

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

