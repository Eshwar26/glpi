"""
GLPI::Agent::XML::Response - Generic server message

Generic message sent by the server to the agent; parses XML into a
Python structure and offers convenience methods for querying options.
"""

from typing import Any, Dict, List, Optional

from . import XML


class Response:
    def __init__(self, *, content: str, **_: Any) -> None:
        xml = XML(
            force_array=['OPTION', 'PARAM', 'MODEL', 'AUTHENTICATION', 'RANGEIP', 'DEVICE', 'GET', 'WALK'],
            attr_prefix='',
            text_node_key='content',
            string=content,
        )
        if not xml.has_xml():
            raise ValueError("content is not an XML message")

        dumped = xml.dump_as_hash()
        if 'REPLY' not in dumped:
            raise ValueError("content is not an expected XML message")

        self._content: Dict[str, Any] = dumped['REPLY']  # type: ignore[index]

    def getContent(self) -> Dict[str, Any]:
        return self._content

    def getOptionsInfoByName(self, name: str):
        options = self._content.get('OPTION')
        if not isinstance(options, list):
            return None
        return [opt for opt in options if isinstance(opt, dict) and opt.get('NAME') == name]


