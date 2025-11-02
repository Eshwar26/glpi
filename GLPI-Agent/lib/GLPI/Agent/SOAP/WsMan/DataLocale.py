# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class DataLocale(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::DataLocale
    WSMan DataLocale node handling.
    """
    xmlns = 'p'
    
    def __init__(self, locale):
        """
        Initialize a DataLocale node with locale-specific attributes.
        
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