# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node

class CommandState(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::CommandState
    WSMan CommandState node handling.
    """
    xmlns = 'rsp'
    
    @staticmethod
    def support():
        return {
            'ExitCode': "rsp:ExitCode",
        }
    
    def done(self, cid=None):
        """
        Check if the command state is done.
        
        Args:
            cid: Optional CommandId to verify against
            
        Returns:
            bool: True if state is done (and CommandId matches if provided), False otherwise
        """
        if cid:
            thiscid = self.attribute("CommandId")
            if not thiscid or thiscid != cid:
                return False
        
        done_url = "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/CommandState/Done"
        state = self.attribute("State")
        
        return bool(state and state == done_url)
    
    def exitcode(self):
        """
        Get the exit code as a string.
        
        Returns:
            str or None: The exit code string, or None if not found
        """
        exitcode = self.get('ExitCode')
        if not exitcode:
            return None
        
        return exitcode.string()


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.