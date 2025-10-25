"""
GLPI Agent Task RemoteInventory Remote Modules
"""

from GLPI.Agent.Task.RemoteInventory.Remote.Ssh import Ssh
from GLPI.Agent.Task.RemoteInventory.Remote.Winrm import Winrm

__all__ = ['Ssh', 'Winrm']

