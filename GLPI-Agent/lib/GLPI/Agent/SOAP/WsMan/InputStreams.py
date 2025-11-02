# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.identify import Identify

class IdentifyResponse(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::IdentifyResponse
    WSMan IdentifyResponse node handling.
    """
    xmlns = 'wsmid'
    
    @staticmethod
    def values():
        """
        Get the list of response values.
        
        Returns:
            list: List of value names
        """
        return ['ProtocolVersion', 'ProductVendor', 'ProductVersion']
    
    def isvalid(self):
        """
        Validate that the response has the correct namespace.
        
        Returns:
            bool: True if the namespace matches Identify.xsd, False otherwise
        """
        xsd = self.attribute(f"xmlns:{self.xmlns}")
        
        return xsd == Identify.xsd if xsd else False
    
    def ProductVendor(self):
        """
        Get the ProductVendor value.
        
        Returns:
            str: The ProductVendor string value
        """
        product_vendor = self.get('ProductVendor')
        return product_vendor.string() if product_vendor else None
    
    def ProductVersion(self):
        """
        Get the ProductVersion value.
        
        Returns:
            str: The ProductVersion string value
        """
        product_version = self.get('ProductVersion')
        return product_version.string() if product_version else None


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.