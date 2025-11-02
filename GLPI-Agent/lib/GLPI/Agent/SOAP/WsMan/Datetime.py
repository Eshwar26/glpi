# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
import re

class Datetime(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Datetime
    WSMan Datetime node handling with format conversion.
    """
    xmlns = 'cim'
    
    def __init__(self, datetime):
        """
        Initialize a Datetime node with format conversion.
        
        Args:
            datetime: The datetime string to convert and store
        """
        # Convert Datetime format
        # Pattern 1: YYYY-MM-DDT00:00:00Z -> MM/DD/YYYY
        match1 = re.match(r'^(\d{4})-(\d{2})-(\d{2})T00:00:00Z$', datetime)
        if match1:
            year, month, day = match1.groups()
            datetime = f"{month}/{day}/{year}"
        else:
            # Pattern 2: YYYY-MM-DDTHH:MM:SS -> YYYY-MM-DD HH:MM:SS
            match2 = re.match(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', datetime)
            if match2:
                year, month, day, hour, minute, second = match2.groups()
                datetime = f"{year}-{month}-{day} {hour}:{minute}:{second}"
        
        # Call parent constructor with converted datetime string
        super().__init__(datetime)


# Note: The package structure is handled by module imports.
# xmlns is a class attribute.