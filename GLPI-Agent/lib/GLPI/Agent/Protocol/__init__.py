"""
GLPI Agent Protocol Package

Protocol message handlers for communication with GLPI server.
"""

from GLPI.Agent.Protocol.Message import ProtocolMessage
from GLPI.Agent.Protocol.Answer import Answer
from GLPI.Agent.Protocol.Contact import Contact
from GLPI.Agent.Protocol.GetParams import GetParams
from GLPI.Agent.Protocol.Inventory import Inventory

__all__ = ['ProtocolMessage', 'Answer', 'Contact', 'GetParams', 'Inventory']

