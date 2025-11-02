from typing import Any, List, Optional, Union

# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.attribute import Attribute
# from glpi.agent.tools import first  # Assuming first() is like any() or first match

# Define placeholders if needed
def first(iterable: List[Any], condition: Any) -> bool:
    """
    Mimics Perl's first { condition } @array, returns true if any matches.
    """
    return any(condition(item) for item in iterable)


class Action(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Action
    WSMan Action node handling.
    """
    xmlns = 'a'

    actions = {
        'command': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Command",
        'commandresponse': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/CommandResponse",
        'create': "http://schemas.xmlsoap.org/ws/2004/09/transfer/Create",
        'createresponse': "http://schemas.xmlsoap.org/ws/2004/09/transfer/CreateResponse",
        'delete': "http://schemas.xmlsoap.org/ws/2004/09/transfer/Delete",
        'deleteresponse': "http://schemas.xmlsoap.org/ws/2004/09/transfer/DeleteResponse",
        'receive': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Receive",
        'receiveresponse': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/ReceiveResponse",
        'signal': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Signal",
        'signalresponse': "http://schemas.microsoft.com/wbem/wsman/1/windows/shell/SignalResponse",
        'get': "http://schemas.xmlsoap.org/ws/2004/09/transfer/Get",
        'enumerate': "http://schemas.xmlsoap.org/ws/2004/09/enumeration/Enumerate",
        'enumerateresponse': "http://schemas.xmlsoap.org/ws/2004/09/enumeration/EnumerateResponse",
        'pull': "http://schemas.xmlsoap.org/ws/2004/09/enumeration/Pull",
        'pullresponse': "http://schemas.xmlsoap.org/ws/2004/09/enumeration/PullResponse",
        'end': "http://schemas.microsoft.com/wbem/wsman/1/wsman/End",
        'fault': [
            "http://schemas.dmtf.org/wbem/wsman/1/wsman/fault",
            "http://schemas.xmlsoap.org/ws/2004/08/addressing/fault",
        ],
    }

    def __new__(cls, action: str):
        url = cls.actions.get(action, action)
        # Assuming Attribute.must_understand() returns an attribute instance
        must_understand_attr = Attribute.must_understand()
        instance = super().__new__(cls)
        # SUPER::new equivalent: initialize with attributes
        # Assuming Node.__init__ takes *args for attributes
        instance.__init__(must_understand_attr, url)
        return instance

    def set(self, action: str) -> Optional[str]:
        if action not in self.actions:
            return None
        return self.string(self.actions[action])

    def is_action(self, action: str) -> bool:
        if action not in self.actions:
            return False
        current_string = self.string()
        action_value = self.actions[action]
        if isinstance(action_value, list):
            return first([current_string == url for url in action_value])
        return current_string == action_value

    def what(self) -> str:
        url = self.string()
        for known, known_url in self.actions.items():
            if isinstance(known_url, list):
                if url in known_url:
                    return known
            elif url == known_url:
                return known
        return url


# Note: In Python, the package structure is handled by module imports.
# The xmlns is a class attribute.
# The 'is' method is renamed to 'is_action' to avoid Python keyword conflict.
# Adjust 'first' import or definition as per GLPI::Agent::Tools.