from typing import Dict

# Assuming the following are imported or defined elsewhere:
# from glpi.agent.soap.wsman.node import Node
# from glpi.agent.soap.wsman.fault import Fault
# from glpi.agent.soap.wsman.enumerateresponse import EnumerateResponse


class Body(Node):
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Body
    WSMan Body node handling.
    """
    xmlns = 's'

    @staticmethod
    def support() -> Dict[str, str]:
        return {
            'IdentifyResponse': "wsmid:IdentifyResponse",
            'Fault': "s:Fault",
            'EnumerateResponse': "n:EnumerateResponse",
            'PullResponse': "n:PullResponse",
            'Shell': "rsp:Shell",
            'ReceiveResponse': "rsp:ReceiveResponse",
            'ResourceCreated': "x:ResourceCreated",
            'CommandResponse': "rsp:CommandResponse",
        }

    def fault(self):
        fault = self.get('Fault')
        return fault or Fault()

    def enumeration(self, ispull: bool = False):
        key = 'PullResponse' if ispull else 'EnumerateResponse'
        enum = self.get(key)
        return enum or EnumerateResponse()