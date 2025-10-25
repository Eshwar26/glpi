#!/usr/bin/env python3
"""
GLPI Agent XML Handler - Python Implementation

XML parsing and generation using lxml library.
Provides functionality to read/write XML with various options.
"""

import os
from typing import Any, Dict, List, Optional, Union
from lxml import etree


class XMLHandler:
    """
    XML handler for GLPI Agent.
    
    Provides XML parsing, generation, and conversion between
    XML and Python dictionaries.
    """
    
    def __init__(self, **params: Any):
        """
        Initialize XML handler.
        
        Args:
            **params: Parameters including:
                - string: XML string to parse
                - file: XML file to parse
                - force_array: List of keys to force as arrays
                - text_node_key: Key name for text nodes (default: '#text')
                - attr_prefix: Prefix for attributes (default: '-')
                - skip_attr: Skip attributes when parsing
                - first_out: List of keys to output first
                - no_xml_decl: Skip XML declaration
                - xml_format: Format output (pretty print)
                - is_plist: Parse as plist format
                - tag_compression: Use compressed tags
        """
        self._xml: Optional[etree._Element] = None
        self._parser = etree.XMLParser(
            remove_blank_text=True,
            recover=True,
            no_network=True
        )
        
        # Configuration options
        self._force_array: Optional[List[str]] = params.get('force_array')
        self._text_node_key: str = params.get('text_node_key', '#text')
        self._attr_prefix: str = params.get('attr_prefix', '-')
        self._skip_attr: bool = params.get('skip_attr', False)
        self._first_out: Optional[List[str]] = params.get('first_out')
        self._no_xml_decl: bool = params.get('no_xml_decl', False)
        self._xml_format: bool = params.get('xml_format', True)
        self._is_plist: bool = params.get('is_plist', False)
        self._tag_compression: bool = params.get('tag_compression', False)
        
        # Parse input if provided
        if params.get('string'):
            self.string(params['string'])
        elif params.get('file'):
            self.file(params['file'])
    
    def _is_xml(self) -> bool:
        """Check if valid XML is loaded."""
        return self._xml is not None and isinstance(self._xml, etree._Element)
    
    def has_xml(self) -> bool:
        """Check if XML document is loaded."""
        return self._xml is not None
    
    def string(self, xml_string: str) -> 'XMLHandler':
        """
        Parse XML from string.
        
        Args:
            xml_string: XML content as string
            
        Returns:
            Self for chaining
        """
        if not xml_string:
            return self
        
        try:
            self._xml = etree.fromstring(
                xml_string.encode('utf-8'),
                parser=self._parser
            )
        except etree.XMLSyntaxError:
            self._xml = None
        
        return self
    
    def file(self, file_path: str) -> 'XMLHandler':
        """
        Parse XML from file.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            Self for chaining
        """
        if not file_path or not os.path.exists(file_path):
            return self
        
        try:
            tree = etree.parse(file_path, parser=self._parser)
            self._xml = tree.getroot()
        except (etree.XMLSyntaxError, OSError):
            self._xml = None
        
        return self
    
    def _build_xml(self, data: Union[Dict, str], parent: Optional[etree._Element] = None) -> etree._Element:
        """
        Build XML tree from dictionary.
        
        Args:
            data: Dictionary or string to convert
            parent: Parent element to append to
            
        Returns:
            Root element
        """
        if parent is None:
            # Create root element
            if not isinstance(data, dict) or len(data) != 1:
                raise ValueError("Root must be a dict with single key")
            
            root_key = list(data.keys())[0]
            root = etree.Element(root_key)
            
            root_value = data[root_key]
            if isinstance(root_value, dict):
                self._build_xml(root_value, root)
            elif isinstance(root_value, str):
                root.text = root_value
            elif root_value is not None:
                root.text = str(root_value)
            
            return root
        
        # Build child elements
        if not isinstance(data, dict):
            return parent
        
        # Determine key order
        keys = list(data.keys())
        if self._first_out:
            first_keys = [k for k in self._first_out if k in keys]
            other_keys = [k for k in keys if k not in first_keys]
            keys = first_keys + sorted(other_keys)
        else:
            keys = sorted(keys)
        
        for key in keys:
            value = data[key]
            
            if value is None:
                continue
            
            # Handle attributes (keys starting with -)
            if key.startswith('-'):
                attr_name = key[1:]
                parent.set(attr_name, str(value))
            
            # Handle text nodes
            elif key == self._text_node_key:
                parent.text = str(value)
            
            # Handle regular elements
            else:
                if isinstance(value, dict):
                    child = etree.SubElement(parent, key)
                    self._build_xml(value, child)
                
                elif isinstance(value, list):
                    for item in value:
                        child = etree.SubElement(parent, key)
                        if isinstance(item, dict):
                            self._build_xml(item, child)
                        elif item is not None:
                            child.text = str(item)
                
                else:
                    child = etree.SubElement(parent, key)
                    child.text = str(value)
        
        return parent
    
    def write(self, data: Optional[Dict] = None) -> str:
        """
        Convert dictionary to XML string.
        
        Args:
            data: Dictionary to convert (uses loaded XML if None)
            
        Returns:
            XML string
        """
        if data:
            self._xml = self._build_xml(data)
        
        if not self._is_xml():
            return ''
        
        # Convert to string
        xml_bytes = etree.tostring(
            self._xml,
            encoding='utf-8',
            xml_declaration=not self._no_xml_decl,
            pretty_print=self._xml_format
        )
        
        return xml_bytes.decode('utf-8')
    
    def writefile(self, file_path: str, data: Optional[Dict] = None) -> None:
        """
        Write XML to file.
        
        Args:
            file_path: Output file path
            data: Dictionary to convert (uses loaded XML if None)
        """
        xml_string = self.write(data)
        if not xml_string:
            return
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
    
    def dump_as_hash(self, node: Optional[etree._Element] = None) -> Any:
        """
        Convert XML to dictionary structure.
        
        Args:
            node: XML element to convert (uses root if None)
            
        Returns:
            Dictionary representation of XML
        """
        if node is None:
            if not self._is_xml():
                return None
            node = self._xml
        
        result = {}
        node_name = node.tag
        
        # Process child nodes
        children_dict = {}
        text_content = ''
        
        for child in node:
            if isinstance(child, etree._Comment):
                continue
            
            child_data = self.dump_as_hash(child)
            child_name = child.tag
            
            if child_name in children_dict:
                # Convert to array if multiple children with same name
                if not isinstance(children_dict[child_name], list):
                    children_dict[child_name] = [children_dict[child_name]]
                children_dict[child_name].append(child_data)
            else:
                # Check if should force as array
                force_array = (
                    self._force_array and
                    child_name in self._force_array
                )
                if force_array:
                    children_dict[child_name] = [child_data]
                else:
                    children_dict[child_name] = child_data
        
        # Get text content
        if node.text:
            text_content = node.text.strip()
        
        # Get attributes
        if not self._skip_attr and node.attrib:
            for attr_name, attr_value in node.attrib.items():
                attr_key = f"{self._attr_prefix}{attr_name}"
                children_dict[attr_key] = attr_value
        
        # Build result
        if children_dict:
            if text_content:
                children_dict[self._text_node_key] = text_content
            
            # Simplify if only text node
            if (len(children_dict) == 1 and 
                self._text_node_key in children_dict):
                result[node_name] = children_dict[self._text_node_key]
            else:
                result[node_name] = children_dict
        elif text_content:
            result[node_name] = text_content
        else:
            result[node_name] = ''
        
        return result


if __name__ == "__main__":
    # Test XML handler
    print("=== GLPI Agent XML Handler Tests ===\n")
    
    # Test writing XML from dict
    print("1. Writing XML from dictionary:")
    data = {
        'REQUEST': {
            'DEVICEID': 'test-device-001',
            'QUERY': 'INVENTORY',
            'CONTENT': {
                'HARDWARE': {
                    'NAME': 'test-computer',
                    'MEMORY': '8192'
                },
                'CPUS': [
                    {'NAME': 'Intel i7', 'SPEED': '2400'},
                    {'NAME': 'Intel i7', 'SPEED': '2400'}
                ]
            }
        }
    }
    
    xml = XMLHandler()
    xml_string = xml.write(data)
    print(xml_string)
    print()
    
    # Test parsing XML
    print("2. Parsing XML to dictionary:")
    xml2 = XMLHandler(string=xml_string)
    parsed = xml2.dump_as_hash()
    print(parsed)
    print()
    
    # Test with attributes
    print("3. XML with attributes:")
    data_with_attrs = {
        'root': {
            '-version': '1.0',
            'element': {
                '-id': '123',
                '#text': 'Content'
            }
        }
    }
    
    xml3 = XMLHandler()
    xml_with_attrs = xml3.write(data_with_attrs)
    print(xml_with_attrs)
    print()
    
    # Test force_array
    print("4. Force array option:")
    xml4 = XMLHandler(
        string='<root><item>one</item></root>',
        force_array=['item']
    )
    parsed_array = xml4.dump_as_hash()
    print(parsed_array)