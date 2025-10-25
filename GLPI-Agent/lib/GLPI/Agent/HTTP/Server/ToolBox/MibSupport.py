"""
GLPI Agent HTTP Server ToolBox MIB Support Module

Manages SNMP MIB support configuration.
"""

from typing import Dict, Any

try:
    from GLPI.Agent.HTTP.Server.ToolBox import ToolBox
except ImportError:
    ToolBox = object


class MibSupport(ToolBox if ToolBox != object else object):
    """
    MIB Support page for ToolBox interface.
    
    Manages SNMP MIB configuration.
    """

    MIB_SUPPORT = "mibsupport"

    def __init__(self, **params):
        """Initialize MIB Support page."""
        self.toolbox = params.get('toolbox')
        self.logger = None
        self.name = "MibSupport"
        
        if self.toolbox:
            self.logger = getattr(self.toolbox, 'logger', None)

    def index(self) -> str:
        """Get the page index/path."""
        return self.MIB_SUPPORT

    def log_prefix(self) -> str:
        """Get the log prefix for this page."""
        return "[toolbox plugin, mibsupport] "

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
            'mibsupport_navbar': {
                'category': "Navigation bar",
                'type': "bool" if is_updating else "readonly",
                'value': self.toolbox.yesno(yaml_config.get('mibsupport_navbar')),
                'text': "Show MIB Support in navigation bar",
                'navbar': "MIB Support",
                'link': self.index(),
                'icon': "database",
                'index': 70,
            },
        }

    def update_template_hash(self, hash_data: Dict[str, Any]):
        """
        Update template hash for rendering.
        
        Args:
            hash_data: Template hash to update
        """
        if not hash_data:
            return
        
        hash_data['title'] = "MIB Support"

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

