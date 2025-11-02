# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node


class CommandResponse(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::CommandResponse
    WSMan CommandResponse node handling.
    """
    xmlns = 'rsp'

    @staticmethod
    def support():
        return {
            'CommandId': "rsp:CommandId",
        }


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.