# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class PartComponent(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::PartComponent
    WSMan PartComponent node handling.
    Required if we need to make request on Win32_SystemUsers.
    """
    xmlns = 'p'
    dump_as_string = True
    
    def string(self):
        """
        Get the string representation of the PartComponent.
        
        Returns:
            str or None: Formatted string representation, or None if required elements are missing
        """
        # Get ReferenceParameters
        refparams = self.get("ReferenceParameters")
        if not refparams:
            return None
        
        # Get ResourceURI
        resource = refparams.get("ResourceURI")
        if not resource:
            return None
        
        # Get SelectorSet
        selectorset = refparams.get("SelectorSet")
        if not selectorset:
            return None
        
        # Get Selector
        selector = selectorset.get("Selector")
        if not selector:
            return None
        
        # Build the string starting with ResourceURI followed by a dot
        string = resource.string() + "."
        
        # Iterate through selector nodes
        for node in selector.nodes():
            name = node.attribute("Name")
            text = node.string()
            
            # Add comma if string doesn't end with a dot
            if not string.endswith('.'):
                string += ","
            
            # Append name="text" format
            string += f'{name}="{text}"'
        
        return string


# Note: The package structure is handled by module imports.
# xmlns and dump_as_string are class attributes.