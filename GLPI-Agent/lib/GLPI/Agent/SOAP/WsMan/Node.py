# Base Node class for GLPI Agent SOAP WsMan
import re
import os
import sys
import importlib
from pathlib import Path

# Get the directory where wsman classes are located
_wsman_classes_path = Path(__file__).parent

class Node:
    """
    Equivalent to GLPI::Agent::SOAP::WsMan::Node
    Base class for WSMan node handling.
    """
    xmlns = ""
    xsd = ""
    dump_as_string = False
    
    def __init__(self, *nodes):
        """
        Initialize a Node with optional child nodes, attributes, and text content.
        
        Args:
            *nodes: Variable arguments that can be Attribute objects, Namespace objects,
                   strings, arrays, hashes, or other Node objects
        """
        self._attributes = []
        self._nodes = []
        self._text = None
        
        # List of class names supported by this node
        supported = self.support() or {}
        
        # Convert to list for manipulation
        nodes_list = list(nodes)
        node_class = self.__class__
        
        while nodes_list:
            node = nodes_list.pop(0)
            node_type = type(node).__name__
            
            if node_type == 'Attribute':
                self._attributes.append(node)
            elif node_type == 'Namespace':
                self._attributes.extend(node.attributes())
            elif not isinstance(node, object) or isinstance(node, (str, int, float)):
                # Handle string/scalar values
                if isinstance(node, str) and node == '__nodeclass__' and nodes_list:
                    node_class = self._load_class(nodes_list.pop(0), self._get_namespace())
                elif isinstance(self._text, list):
                    if isinstance(node, list):
                        self._text.extend(node)
                    else:
                        self._text.append(node)
                elif self._text is not None:
                    if isinstance(node, list):
                        self._text = [self._text] + node
                    else:
                        self._text = [self._text, node]
                elif node is not None:
                    self._text = node
            elif isinstance(node, list):
                for obj in node:
                    this = Node(obj)
                    self._nodes.append(this)
            elif isinstance(node, dict):
                for key, value in node.items():
                    if key.startswith('-'):
                        attr_key = key[1:]
                        self._attributes.append(Attribute(attr_key, value))
                        if attr_key == 'xsi:type':
                            match = re.match(r'^p:(.+)$', value)
                            if match:
                                node_class = self._load_class(match.group(1))
                    elif key == '#text':
                        if value is not None:
                            self._text = value
                            # Handle textuuid pattern
                            match = re.match(r'^#textuuid:(.*)$', str(self._text))
                            if match:
                                self._text = match.group(1)
                    else:
                        # Find support mapping
                        support = None
                        for sup_key, sup_val in supported.items():
                            if sup_val == key:
                                support = sup_key
                                break
                        
                        if not support:
                            # Extract class name from key
                            match = re.match(r'^(?:\w+:)?(\w+)$', key)
                            if match:
                                support = match.group(1)
                        
                        # Try to load class if not loaded
                        if support:
                            support_class = self._load_class(support)
                            self._nodes.append(support_class(value))
            else:
                # Other object types
                self._nodes.append(node)
        
        # Change class if needed (simulating re-blessing in Perl)
        if node_class != self.__class__:
            self.__class__ = node_class
    
    @classmethod
    def _load_class(cls, class_name, namespace=None):
        """
        Dynamically load a class or create it if it doesn't exist.
        
        Args:
            class_name: The name of the class to load
            namespace: Optional namespace for the class
            
        Returns:
            class: The loaded or created class
        """
        # Check if already loaded
        try:
            # Try to import from the wsman module
            module_name = f"glpi.agent.soap.wsman.{class_name.lower()}"
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            pass
        
        # Check if file exists
        class_file = _wsman_classes_path / f"{class_name.lower()}.py"
        if class_file.exists():
            try:
                module_name = f"glpi.agent.soap.wsman.{class_name.lower()}"
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
            except Exception as e:
                print(f"Failure while loading {class_name}: {e}", file=sys.stderr)
                return Node
        
        # Create a dynamic class if not found
        if class_name not in globals():
            attrs = {'xmlns': namespace or ''}
            new_class = type(class_name, (Node,), attrs)
            globals()[class_name] = new_class
        
        return globals()[class_name]
    
    def namespace(self):
        """
        Get the namespace declaration for this node.
        
        Returns:
            tuple: (key, value) pair for namespace declaration
        """
        return (f"xmlns:{self.xmlns}", self.xsd)
    
    def _get_namespace(self):
        """
        Extract namespace from attributes.
        
        Returns:
            str or None: The namespace prefix, or None if not found
        """
        if not self._attributes:
            return None
        
        for attr in self._attributes:
            for key in attr.keys():
                if key.startswith('xmlns:'):
                    match = re.match(r'^xmlns:(\w+)$', key)
                    if match:
                        return match.group(1)
        return None
    
    def set_namespace(self):
        """
        Set namespace attribute if not already present.
        """
        # Check if xmlns already exists
        has_xmlns = False
        if self._attributes:
            for attr in self._attributes:
                if any(key.startswith('xmlns:') for key in attr.keys()):
                    has_xmlns = True
                    break
        
        if not has_xmlns:
            ns_key, ns_val = self.namespace()
            self.push(Attribute(ns_key, ns_val))
    
    def reset_namespace(self, *attributes):
        """
        Reset namespace attributes.
        
        Args:
            *attributes: New attributes to set
        """
        if not attributes:
            self._attributes = []
        else:
            self._attributes = list(attributes)
    
    @staticmethod
    def support():
        """
        Override in subclasses to define supported child elements.
        
        Returns:
            dict or None: Mapping of class names to XML qualified names
        """
        return None
    
    @staticmethod
    def values():
        """
        Override in subclasses to define value fields.
        
        Returns:
            list or None: List of value field names
        """
        return None
    
    def get(self, leaf=None):
        """
        Get node content or a specific child node.
        
        Args:
            leaf: Optional class name to filter for specific node
            
        Returns:
            dict or Node: Dictionary representation or specific node
        """
        if leaf:
            if self._nodes:
                for node in self._nodes:
                    if type(node).__name__ == leaf:
                        return node
            return None
        
        nodes = {}
        
        # Process attributes and child nodes
        all_items = (self._attributes or []) + (self._nodes or [])
        for node in all_items:
            insert = node.get()
            
            if isinstance(insert, dict):
                for key, value in insert.items():
                    if key in nodes:
                        if not isinstance(nodes[key], list):
                            nodes[key] = [nodes[key]]
                        nodes[key].append(value)
                    else:
                        nodes[key] = value
            elif isinstance(insert, list):
                i = 0
                while i < len(insert):
                    key = insert[i]
                    value = insert[i + 1] if i + 1 < len(insert) else None
                    if key in nodes:
                        if not isinstance(nodes[key], list):
                            nodes[key] = [nodes[key]]
                        nodes[key].append(value)
                    else:
                        nodes[key] = value
                    i += 2
            elif insert is not None:
                nodes[type(insert).__name__] = insert
        
        if self._text is not None:
            nodes['#text'] = self._text
        
        return {f"{self.xmlns}:{type(self).__name__}": nodes}
    
    def delete(self, node):
        """
        Delete nodes of a specific type.
        
        Args:
            node: Class name of nodes to delete
        """
        if not node or not self._nodes:
            return
        
        self._nodes = [n for n in self._nodes if type(n).__name__ != node]
    
    def nodes(self, filter=None):
        """
        Get child nodes, optionally filtered by type.
        
        Args:
            filter: Optional class name to filter nodes
            
        Returns:
            list: List of matching nodes
        """
        if self._nodes is None:
            return []
        
        if filter:
            return [n for n in self._nodes if type(n).__name__ == filter]
        
        return self._nodes
    
    def push(self, *nodes):
        """
        Add nodes or attributes to this node.
        
        Args:
            *nodes: Nodes or Attributes to add
        """
        if not nodes:
            return
        
        for node in nodes:
            if type(node).__name__ == 'Attribute':
                self._attributes.append(node)
            else:
                self._nodes.append(node)
    
    def attribute(self, key):
        """
        Get the value of a specific attribute.
        
        Args:
            key: Attribute key to look up
            
        Returns:
            Any: The attribute value, or None if not found
        """
        attrs = self.attributes(key)
        if not attrs:
            return None
        
        return attrs[0].get(key)
    
    def attributes(self, key=None):
        """
        Get attributes, optionally filtered by key.
        
        Args:
            key: Optional key to filter attributes
            
        Returns:
            list: List of matching attributes
        """
        if self._attributes is None:
            return []
        
        if key:
            return [attr for attr in self._attributes if attr.get(key)]
        
        return self._attributes
    
    def string(self, string=None):
        """
        Get or set the text content of this node.
        
        Args:
            string: Optional string to set as text content
            
        Returns:
            str: The text content
        """
        if string is not None:
            self._text = string
            return string
        
        nodes = self.nodes()
        if self._text is None and len(nodes) == 1:
            return nodes[0].string()
        
        return self._text if self._text is not None else ''
    
    def reset(self, *nodes):
        """
        Reset child nodes to the provided nodes.
        
        Args:
            *nodes: New nodes to set
        """
        self._nodes = []
        self.push(*nodes)


# Import Attribute here to avoid circular imports
# This should be at the end or handled through proper module structure
# from glpi.agent.soap.wsman.attribute import Attribute