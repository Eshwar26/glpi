# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute

class Namespace(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Namespace
    WSMan Namespace node handling.
    """
    
    # Namespace mappings
    _ns = {
        's': 'http://www.w3.org/2003/05/soap-envelope',
        'a': 'http://schemas.xmlsoap.org/ws/2004/08/addressing',
        'n': 'http://schemas.xmlsoap.org/ws/2004/09/enumeration',
        'w': 'http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd',
        'p': 'http://schemas.microsoft.com/wbem/wsman/1/wsman.xsd',
        'b': 'http://schemas.dmtf.org/wbem/wsman/1/cimbinding.xsd',
        'wsmid': 'http://schemas.dmtf.org/wbem/wsman/identity/1/wsmanidentity.xsd'
    }
    
    def __init__(self, *namespaces):
        """
        Initialize a Namespace node with namespace declarations.
        
        Args:
            *namespaces: Variable arguments for namespace prefixes and URIs.
                        Can be either:
                        - Known prefix (looked up in _ns)
                        - Prefix followed by URI
        """
        attributes = {}
        
        # Convert tuple to list for manipulation
        ns_list = list(namespaces)
        
        while ns_list:
            ns = ns_list.pop(0)
            if ns in self._ns:
                # Use predefined namespace URI
                attributes[f"xmlns:{ns}"] = self._ns[ns]
            else:
                # Next element should be the URI
                if ns_list:
                    uri = ns_list.pop(0)
                    attributes[f"xmlns:{ns}"] = uri
                else:
                    # If no URI provided, skip this namespace
                    break
        
        # Call parent constructor with Attribute object containing all namespace declarations
        super().__init__(Attribute(**attributes))


# Note: The package structure is handled by module imports.
# Namespace mappings are stored as a class attribute.