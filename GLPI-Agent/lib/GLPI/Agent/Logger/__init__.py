"""
GLPI Agent Logger Package

Logger backends for the GLPI Agent.
"""

from GLPI.Agent.Logger.Backend import Backend
from GLPI.Agent.Logger.File import File
from GLPI.Agent.Logger.Stderr import Stderr
from GLPI.Agent.Logger.Syslog import Syslog

__all__ = ['Backend', 'File', 'Stderr', 'Syslog']

