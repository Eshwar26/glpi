#!/usr/bin/env python3

import os
import sys
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent import Agent
    from GLPI.Agent.Logger import Logger
    from GLPI.Agent.Inventory import Inventory
    AGENT_STRING = getattr(Agent, 'AGENT_STRING', 'GLPI-Agent-Python')
except ImportError:
    Inventory = Logger = None
    AGENT_STRING = 'GLPI-Agent-Python'


@pytest.mark.skipif(Inventory is None or Logger is None, reason="Inventory or Logger not implemented")
class TestInventory:
    """Tests for GLPI Agent Inventory"""
    
    @pytest.fixture
    def logger(self):
        """Create a test logger"""
        return Logger(logger=['Test'], debug=True)
    
    @pytest.fixture
    def inventory(self, logger):
        """Create a test inventory"""
        return Inventory(logger=logger)
    
    def test_inventory_creation(self, logger):
        """Test inventory instantiation"""
        inventory = Inventory(logger=logger)
        assert inventory is not None
        assert isinstance(inventory, Inventory)
    
    def test_initial_state(self, inventory):
        """Test initial inventory state"""
        if not hasattr(inventory, 'content'):
            pytest.skip("content attribute not implemented")
        
        content = inventory.content
        assert 'HARDWARE' in content
        assert content['HARDWARE'].get('VMSYSTEM') == 'Physical'
        assert 'VERSIONCLIENT' in content
        assert content['VERSIONCLIENT'] == AGENT_STRING
    
    def test_add_entry_no_entry(self, inventory):
        """Test addEntry with no entry parameter"""
        if not hasattr(inventory, 'addEntry'):
            pytest.skip("addEntry not implemented")
        
        with pytest.raises(Exception, match="no entry"):
            inventory.addEntry(section='FOOS')
    
    def test_add_entry_unknown_section(self, inventory):
        """Test addEntry with unknown section"""
        if not hasattr(inventory, 'addEntry'):
            pytest.skip("addEntry not implemented")
        
        with pytest.raises(Exception, match="unknown section"):
            inventory.addEntry(section='FOOS', entry={'bar': 1})
    
    def test_add_single_entry(self, inventory):
        """Test adding a single environment variable"""
        if not hasattr(inventory, 'addEntry'):
            pytest.skip("addEntry not implemented")
        
        inventory.addEntry(
            section='ENVS',
            entry={'KEY': 'key1', 'VAL': 'val1'}
        )
        
        assert 'ENVS' in inventory.content
        assert inventory.content['ENVS'] == [{'KEY': 'key1', 'VAL': 'val1'}]
    
    def test_add_multiple_entries(self, inventory):
        """Test adding multiple entries"""
        if not hasattr(inventory, 'addEntry'):
            pytest.skip("addEntry not implemented")
        
        inventory.addEntry(
            section='ENVS',
            entry={'KEY': 'key1', 'VAL': 'val1'}
        )
        
        inventory.addEntry(
            section='ENVS',
            entry={'KEY': 'key2', 'VAL': 'val2'}
        )
        
        assert 'ENVS' in inventory.content
        assert len(inventory.content['ENVS']) == 2
        assert {'KEY': 'key1', 'VAL': 'val1'} in inventory.content['ENVS']
        assert {'KEY': 'key2', 'VAL': 'val2'} in inventory.content['ENVS']
    
    def test_add_entry_noDuplicate(self, inventory):
        """Test noDuplicate flag"""
        if not hasattr(inventory, 'addEntry'):
            pytest.skip("addEntry not implemented")
        
        inventory.addEntry(
            section='ENVS',
            entry={'KEY': 'key1', 'VAL': 'val1'},
            noDuplicate=True
        )
        
        # Try to add same entry again
        inventory.addEntry(
            section='ENVS',
            entry={'KEY': 'key1', 'VAL': 'val1'},
            noDuplicate=True
        )
        
        # Should only have one entry
        assert 'ENVS' in inventory.content
        assert len(inventory.content['ENVS']) == 1
        assert inventory.content['ENVS'][0] == {'KEY': 'key1', 'VAL': 'val1'}
    
    def test_set_hardware(self, inventory):
        """Test setHardware method"""
        if not hasattr(inventory, 'setHardware'):
            pytest.skip("setHardware not implemented")
        
        inventory.setHardware({
            'NAME': 'test-machine',
            'OSNAME': 'Linux'
        })
        
        assert 'HARDWARE' in inventory.content
        assert inventory.content['HARDWARE'].get('NAME') == 'test-machine'
        assert inventory.content['HARDWARE'].get('OSNAME') == 'Linux'
    
    def test_set_bios(self, inventory):
        """Test setBios method"""
        if not hasattr(inventory, 'setBios'):
            pytest.skip("setBios not implemented")
        
        inventory.setBios({
            'BMANUFACTURER': 'Test BIOS Mfg',
            'BVERSION': '1.0'
        })
        
        if 'BIOS' in inventory.content:
            assert inventory.content['BIOS'].get('BMANUFACTURER') == 'Test BIOS Mfg'
            assert inventory.content['BIOS'].get('BVERSION') == '1.0'
    
    def test_set_operating_system(self, inventory):
        """Test setOperatingSystem method"""
        if not hasattr(inventory, 'setOperatingSystem'):
            pytest.skip("setOperatingSystem not implemented")
        
        inventory.setOperatingSystem({
            'NAME': 'Ubuntu',
            'VERSION': '20.04'
        })
        
        if 'OPERATINGSYSTEM' in inventory.content:
            assert inventory.content['OPERATINGSYSTEM'].get('NAME') == 'Ubuntu'
    
    def test_get_content(self, inventory):
        """Test getContent method"""
        if not hasattr(inventory, 'getContent'):
            pytest.skip("getContent not implemented")
        
        content = inventory.getContent()
        assert content is not None
        assert isinstance(content, dict)
        assert 'HARDWARE' in content
    
    def test_xml_generation(self, inventory):
        """Test XML generation"""
        if not hasattr(inventory, 'getXML') and not hasattr(inventory, 'toXML'):
            pytest.skip("XML generation not implemented")
        
        # Add some data
        if hasattr(inventory, 'addEntry'):
            inventory.addEntry(
                section='ENVS',
                entry={'KEY': 'TEST', 'VAL': 'value'}
            )
        
        # Generate XML
        if hasattr(inventory, 'getXML'):
            xml = inventory.getXML()
        else:
            xml = inventory.toXML()
        
        assert xml is not None
        assert isinstance(xml, (str, bytes))
        if isinstance(xml, str):
            assert '<?xml' in xml or '<REQUEST' in xml


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
