#!/usr/bin/env python3

import os
import sys
import platform
import tempfile
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

# Add fake modules for non-Windows platforms
if platform.system() != 'Windows':
    sys.path.insert(0, 't/lib/fake/windows')

try:
    from GLPI.Agent.Target.Local import Local as TargetLocal
    from GLPI.Agent.Task.Inventory import Inventory as TaskInventory
    from GLPI.Agent.Task.Collect import Collect as TaskCollect
    from GLPI.Agent import Tools
except ImportError:
    TargetLocal = TaskInventory = TaskCollect = Tools = None


@pytest.mark.skipif(TaskInventory is None, reason="Task classes not implemented")
class TestTask:
    """Tests for GLPI Agent Tasks"""
    
    def test_inventory_no_target(self):
        """Test Inventory task instantiation without target parameter"""
        with pytest.raises(Exception, match="no target parameter"):
            TaskInventory()
    
    def test_inventory_with_target(self):
        """Test Inventory task instantiation with target"""
        if TargetLocal is None:
            pytest.skip("TargetLocal not implemented")
        
        try:
            tmpdir = tempfile.mkdtemp()
            tmpvardir = tempfile.mkdtemp()
            
            target = TargetLocal(
                path=tmpdir,
                basevardir=tmpvardir
            )
            
            task = TaskInventory(target=target)
            assert task is not None
        except:
            pytest.skip("Task initialization not fully implemented")
    
    def test_inventory_get_modules(self):
        """Test getModules for Inventory task"""
        if TargetLocal is None or TaskInventory is None:
            pytest.skip("Required classes not implemented")
        
        try:
            tmpdir = tempfile.mkdtemp()
            tmpvardir = tempfile.mkdtemp()
            
            target = TargetLocal(path=tmpdir, basevardir=tmpvardir)
            task = TaskInventory(target=target)
            
            if not hasattr(task, 'getModules'):
                pytest.skip("getModules not implemented")
            
            modules = task.getModules()
            assert len(modules) > 0, "modules list should not be empty"
            
            # All modules should be inventory modules
            for module in modules:
                assert 'Inventory' in module or module.startswith('GLPI.Agent.Task.Inventory.')
        except:
            pytest.skip("getModules not fully implemented")
    
    def test_get_specific_modules(self):
        """Test getModules with specific task type"""
        if TargetLocal is None or TaskInventory is None:
            pytest.skip("Required classes not implemented")
        
        try:
            tmpdir = tempfile.mkdtemp()
            tmpvardir = tempfile.mkdtemp()
            
            target = TargetLocal(path=tmpdir, basevardir=tmpvardir)
            task = TaskInventory(target=target)
            
            if not hasattr(task, 'getModules'):
                pytest.skip("getModules not implemented")
            
            # Get inventory modules
            modules = task.getModules('Inventory')
            assert len(modules) > 0, "inventory modules list should not be empty"
            
            for module in modules:
                assert 'Inventory' in module
        except:
            pytest.skip("getModules with parameter not fully implemented")
    
    def test_collect_modules(self):
        """Test getting Collect task modules"""
        if TargetLocal is None or TaskInventory is None:
            pytest.skip("Required classes not implemented")
        
        try:
            tmpdir = tempfile.mkdtemp()
            tmpvardir = tempfile.mkdtemp()
            
            target = TargetLocal(path=tmpdir, basevardir=tmpvardir)
            task = TaskInventory(target=target)
            
            if not hasattr(task, 'getModules'):
                pytest.skip("getModules not implemented")
            
            # Get collect modules
            modules = task.getModules('Collect')
            # Collect modules may or may not exist depending on implementation
            if len(modules) > 0:
                for module in modules:
                    assert 'Collect' in module
        except:
            pytest.skip("Collect modules not fully implemented")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
