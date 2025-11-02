# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class ResourceURI(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::ResourceURI
    WSMan ResourceURI node handling.
    """
    xmlns = 'w'

    def __init__(self, url):
        """
        Initialize a ResourceURI node.

        Args:
            url (str): The resource URL.
        """
        # Call the parent (Node) constructor with must_understand() attribute and the URL.
        super().__init__(Attribute.must_understand(), url)