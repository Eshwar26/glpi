"""
GLPI Agent Task RemoteInventory Module
"""

from GLPI.Agent.Task.RemoteInventory.Version import VERSION
from GLPI.Agent.Task.RemoteInventory.Remotes import Remotes
from GLPI.Agent.Task.RemoteInventory.Remote import Remote

__all__ = ['VERSION', 'Remotes', 'Remote']
__version__ = VERSION

