"""
GLPI Agent Task Module

This package contains all task implementations for the GLPI Agent.
"""

from GLPI.Agent.Task.Collect import CollectTask
from GLPI.Agent.Task.WakeOnLan import WakeOnLanTask
from GLPI.Agent.Task.ESX import ESXTask
from GLPI.Agent.Task.NetDiscovery import NetDiscoveryTask
from GLPI.Agent.Task.NetInventory import NetInventoryTask
from GLPI.Agent.Task.RemoteInventory import RemoteInventoryTask

__all__ = [
    'CollectTask',
    'WakeOnLanTask',
    'ESXTask',
    'NetDiscoveryTask',
    'NetInventoryTask',
    'RemoteInventoryTask',
]

