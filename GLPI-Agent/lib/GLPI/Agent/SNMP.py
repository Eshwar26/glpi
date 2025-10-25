"""
GLPI Agent SNMP - Base class for SNMP client (Python)

This object is used by the agent to perform SNMP queries.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple, Union


IndexKey = Union[int, str, Tuple[int, ...]]


class SNMP:
    """Base SNMP client interface.

    Concrete implementations must provide `get`, `walk`, VLAN context
    switching methods, etc.
    """

    def switch_vlan_context(self, vlan_id: int) -> None:
        """Switch to a new vlan-specific context.

        Implementations may create a new SNMP session (v1/v2) using a
        community derived from the original one, or set the relevant context
        for SNMPv3.
        """
        raise NotImplementedError

    def reset_original_context(self) -> None:
        """Reset to original SNMP context."""
        raise NotImplementedError

    def get(self, oid: str) -> Any:
        """Return the value for the SNMP object with the given OID."""
        raise NotImplementedError

    def walk(self, oid: str) -> Optional[Dict[IndexKey, Any]]:
        """Return all values from the SNMP table with given OID, indexed by their index."""
        raise NotImplementedError

    def get_first(self, oid: str) -> Any:
        """Return the first non-null value from the SNMP table for the given OID.

        Mirrors Perl logic: iterate values ordered by numeric index and return
        the first truthy value.
        """
        values = self.walk(oid)
        if not values:
            return None

        def sort_key(key: IndexKey) -> Tuple:
            # Numeric tuple for robust ordering: support int, numeric strings, and dotted indices
            if isinstance(key, tuple):
                return key
            if isinstance(key, int):
                return (key,)
            s = str(key)
            parts = s.split('.') if '.' in s else [s]
            if all(p.isdigit() for p in parts):
                return tuple(int(p) for p in parts)
            # Fallback to lexical ordering
            return (s,)

        for k in sorted(values.keys(), key=sort_key):
            v = values.get(k)
            if v:
                return v
        return None

