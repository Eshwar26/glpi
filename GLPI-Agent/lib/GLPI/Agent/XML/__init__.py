"""
GLPI Agent XML Package

Provides a lightweight XML reader/writer compatible with the agent's
expected structure, plus convenience exports for query/response modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import xml.etree.ElementTree as ET


JsonLike = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class XML:
    """Minimal XML helper to match GLPI agent expectations.

    Features:
    - Parse XML into nested dict/list structure
    - Serialize dict/list structure into XML
    - Control array coercion via force_array
    - Control text node capture via text_node_key
    - Optional attribute handling via attr_prefix
    """

    def __init__(
        self,
        *,
        force_array: Optional[List[str]] = None,
        attr_prefix: str = "@",
        text_node_key: str = "content",
        string: Optional[str] = None,
    ) -> None:
        self.force_array = set(force_array or [])
        self.attr_prefix = attr_prefix
        self.text_node_key = text_node_key
        self._xml_string: Optional[str] = None
        self._root: Optional[ET.Element] = None

        if string is not None:
            self.string(string)

    # Parsing API
    def string(self, xml_string: str) -> "XML":
        """Load XML from a string and return self for chaining."""
        self._xml_string = xml_string
        try:
            self._root = ET.fromstring(xml_string)
        except ET.ParseError:
            self._root = None
        return self

    def has_xml(self) -> bool:
        return self._root is not None

    def dump_as_hash(self) -> Dict[str, Any]:
        """Return a JSON-like representation of the XML tree."""
        if not self._root:
            return {}
        return {self._root.tag: self._element_to_obj(self._root)}

    # Writing API
    def write(self, obj: Dict[str, Any]) -> str:
        """Serialize a JSON-like object into an XML string."""
        if not isinstance(obj, dict) or len(obj) != 1:
            raise ValueError("Top-level XML object must be a single-key dict")

        root_tag, root_value = next(iter(obj.items()))
        root_elem = ET.Element(root_tag)
        self._obj_to_element(root_elem, root_value)
        return ET.tostring(root_elem, encoding="unicode")

    # Internal helpers
    def _element_to_obj(self, elem: ET.Element) -> JsonLike:
        children = list(elem)
        has_children = len(children) > 0
        obj: Dict[str, JsonLike] = {}

        # Attributes
        for attr_key, attr_val in elem.attrib.items():
            key = f"{self.attr_prefix}{attr_key}" if self.attr_prefix else attr_key
            obj[key] = attr_val

        # Children
        if has_children:
            tag_to_values: Dict[str, List[JsonLike]] = {}
            for child in children:
                tag_to_values.setdefault(child.tag, []).append(self._element_to_obj(child))

            for tag, values in tag_to_values.items():
                if len(values) > 1 or tag in self.force_array:
                    obj[tag] = values
                else:
                    obj[tag] = values[0]

        # Text content
        text = (elem.text or "").strip()
        if text:
            if has_children or elem.attrib:
                obj[self.text_node_key] = text
            else:
                # Leaf node with only text
                return text

        return obj

    def _obj_to_element(self, parent: ET.Element, value: JsonLike) -> None:
        if isinstance(value, dict):
            for key, child_val in value.items():
                if key.startswith(self.attr_prefix) and self.attr_prefix:
                    parent.set(key[len(self.attr_prefix) :], str(child_val))
                    continue
                if key == self.text_node_key and not isinstance(child_val, (dict, list)):
                    parent.text = "" if child_val is None else str(child_val)
                    continue

                # Nested element(s)
                if isinstance(child_val, list):
                    for item in child_val:
                        child = ET.SubElement(parent, key)
                        self._obj_to_element(child, item)
                else:
                    child = ET.SubElement(parent, key)
                    self._obj_to_element(child, child_val)
        elif isinstance(value, list):
            # Anonymous array – not typical for our usage, but support anyway
            for item in value:
                child = ET.SubElement(parent, "ITEM")
                self._obj_to_element(child, item)
        else:
            parent.text = "" if value is None else str(value)


# Convenience exports
from .Query import Query  # noqa: E402
from .Response import Response  # noqa: E402
from .Query.Inventory import Inventory as InventoryQuery  # noqa: E402
from .Query.Prolog import Prolog  # noqa: E402

__all__ = ["XML", "Query", "Response", "InventoryQuery", "Prolog"]


