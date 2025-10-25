"""
GLPI Agent HTTP Server ToolBox Remotes Module

Manages remote targets for inventory and discovery.
"""

from typing import Dict, Any

try:
    from GLPI.Agent.HTTP.Server.ToolBox import ToolBox
except ImportError:
    ToolBox = object


class Remotes(ToolBox if ToolBox != object else object):
    """
    Remotes page for ToolBox interface.
    
    Manages remote target configuration.
    """

    REMOTES = "remotes"

    def __init__(self, **params):
        """Initialize Remotes page."""
        self.toolbox = params.get('toolbox')
        self.logger = None
        self.name = "Remotes"
        
        if self.toolbox:
            self.logger = getattr(self.toolbox, 'logger', None)

    def index(self) -> str:
        """Get the page index/path."""
        return self.REMOTES

    def log_prefix(self) -> str:
        """Get the log prefix for this page."""
        return "[toolbox plugin, remotes] "

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
            'remotes_navbar': {
                'category': "Navigation bar",
                'type': "bool" if is_updating else "readonly",
                'value': self.toolbox.yesno(yaml_config.get('remotes_navbar')),
                'text': "Show Remotes in navigation bar",
                'navbar': "Remotes",
                'link': self.index(),
                'icon': "server",
                'index': 60,
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
        
        hash_data['title'] = "Remotes"

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

