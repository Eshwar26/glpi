# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node


class CommandLine(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::CommandLine
    WSMan CommandLine node handling.
    """
    xmlns = 'rsp'


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.