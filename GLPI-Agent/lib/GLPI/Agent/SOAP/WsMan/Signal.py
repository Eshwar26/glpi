# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class Signal(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Signal
    WSMan Signal node handling.
    """
    xmlns = 'rsp'


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.