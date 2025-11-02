# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node


class CommandId(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::CommandId
    WSMan CommandId node handling.
    """
    xmlns = 'rsp'


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.