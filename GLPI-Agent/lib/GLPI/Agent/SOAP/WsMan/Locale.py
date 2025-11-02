# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class Locale(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Locale
    WSMan Locale node handling.
    """
    xmlns = 'w'
    
    def __init__(self, locale):
        """
        Initialize a Locale node with locale-specific attributes.
        
        Args:
            locale: The locale string (e.g., 'en-US', 'fr-FR')
        """
        # Call parent constructor with Attribute objects
        super().__init__(
            Attribute.must_understand("false"),
            Attribute("xml:lang", locale)
        )


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.