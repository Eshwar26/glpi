"""
GLPI::Agent::XML::Query - Base class for agent messages

Abstract base for all XML query messages sent by the agent to the server.
"""

from typing import Any, Dict

from . import XML


class Query:
    """Base XML query builder."""

    def __init__(self, **params: Any) -> None:
        if 'query' not in params or not params['query']:
            raise ValueError("no query parameter for XML query")

        # Uppercase keys like the Perl implementation
        self._h: Dict[str, Any] = {}
        for key, value in params.items():
            self._h[key.upper()] = value

    def getContent(self) -> str:
        """Generate XML content for the request."""
        return XML().write({'REQUEST': self._h})


