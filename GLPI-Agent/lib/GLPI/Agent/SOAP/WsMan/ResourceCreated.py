# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class ResourceCreated(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::ResourceCreated
    WSMan ResourceCreated node handling.
    """
    xmlns = 'x'

    @classmethod
    def support(cls):
        """
        Returns the supported reference parameters mapping.

        Returns:
            dict: Mapping of supported reference parameters.
        """
        return {
            'ReferenceParameters': 'a:ReferenceParameters',
        }