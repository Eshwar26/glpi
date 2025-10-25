"""
GLPI Agent HTTP Server ToolBox Scheduling Module

Manages scheduled network discovery and inventory jobs.
"""

from typing import Dict, Any

try:
    from GLPI.Agent.HTTP.Server.ToolBox import ToolBox
except ImportError:
    ToolBox = object


class Scheduling(ToolBox if ToolBox != object else object):
    """
    Scheduling page for ToolBox interface.
    
    Manages scheduled jobs for network tasks.
    """

    JOBS = "jobs"

    def __init__(self, **params):
        """Initialize Scheduling page."""
        self.toolbox = params.get('toolbox')
        self.logger = None
        self.name = "Scheduling"
        
        if self.toolbox:
            self.logger = getattr(self.toolbox, 'logger', None)

    def index(self) -> str:
        """Get the page index/path."""
        return self.JOBS

    def log_prefix(self) -> str:
        """Get the log prefix for this page."""
        return "[toolbox plugin, scheduling] "

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
            'scheduling_navbar': {
                'category': "Navigation bar",
                'type': "bool" if is_updating else "readonly",
                'value': self.toolbox.yesno(yaml_config.get('scheduling_navbar')),
                'text': "Show Scheduling in navigation bar",
                'navbar': "Scheduling",
                'link': self.index(),
                'icon': "calendar",
                'index': 30,
            },
            'jobs_yaml': {
                'category': "Toolbox plugin configuration",
                'type': "option" if is_updating else "readonly",
                'value': yaml_config.get('jobs_yaml') or (
                    "" if is_updating else "[default]"
                ),
                'options': self.toolbox.yaml_files() if hasattr(self.toolbox, 'yaml_files') else [],
                'text': "Jobs YAML file",
                'yaml_base': self.JOBS,
            }
        }

    def update_template_hash(self, hash_data: Dict[str, Any]):
        """
        Update template hash for rendering.
        
        Args:
            hash_data: Template hash to update
        """
        if not hash_data:
            return
        
        hash_data['title'] = "Job Scheduling"

    def need_init(self) -> bool:
        """Check if page needs initialization."""
        return False

    def register_events_cb(self) -> bool:
        """Check if page should register for events."""
        return True

    def events_cb(self, event: str) -> bool:
        """
        Handle events.
        
        Args:
            event: Event string
            
        Returns:
            True if event was handled
        """
        return False

    def handle_form(self, form: Dict[str, Any]):
        """
        Handle form submission.
        
        Args:
            form: Form data dictionary
        """
        pass

