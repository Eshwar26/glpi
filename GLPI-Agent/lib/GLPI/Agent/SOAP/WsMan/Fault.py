# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.reason import Reason

class Fault(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Fault
    WSMan Fault node handling.
    """
    xmlns = 's'
    
    @staticmethod
    def support():
        return {
            'Reason': "s:Reason",
            'Code': "s:Code",
        }
    
    def reason(self):
        """
        Get the Reason node from the fault.
        
        Returns:
            Reason: The reason node, or a new one if not found
        """
        reason_node = self.get('Reason')
        
        return reason_node if reason_node else Reason()
    
    def errorCode(self):
        """
        Extract the error code from the fault detail.
        
        Returns:
            str or int: The error code, or 0 if not found
        """
        code = None
        
        detail = self.get('Detail')
        
        if detail:
            # Try to get WMI error first
            wmierror = detail.get('MSFT_WmiError_Type')
            if wmierror:
                error_code_node = wmierror.get('error_Code')
                if error_code_node:
                    code = error_code_node.string()
            
            # If no WMI error, try WSManFault
            if not code:
                wsmanerror = detail.get('WSManFault')
                if wsmanerror:
                    code = wsmanerror.attribute('Code')
        
        return code if code else 0


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.