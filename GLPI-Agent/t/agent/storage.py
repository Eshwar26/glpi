#!/usr/bin/env python3

import os
import sys
import platform
import tempfile
import shutil
import stat
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Storage import Storage
except ImportError:
    Storage = None


@pytest.mark.skipif(Storage is None, reason="Storage class not implemented")
class TestStorage:
    """Tests for GLPI Agent Storage"""
    
    @pytest.fixture
    def temp_basedir(self):
        """Create temporary base directory for tests"""
        basedir = tempfile.mkdtemp()
        yield basedir
        if not os.environ.get('TEST_DEBUG'):
            shutil.rmtree(basedir, ignore_errors=True)
    
    def test_no_directory_parameter(self):
        """Test instantiation without directory parameter"""
        with pytest.raises(Exception, match="no directory parameter"):
            Storage()
    
    @pytest.mark.skipif(platform.system() == 'Windows', reason="chmod doesn't work on Windows")
    def test_non_writable_directory(self, temp_basedir):
        """Test instantiation with non-writable directory"""
        # Skip if running as root
        if hasattr(os, 'getuid') and os.getuid() == 0:
            pytest.skip("Test not applicable when running as root")
        
        readdir = os.path.join(temp_basedir, 'read')
        os.mkdir(readdir)
        os.chmod(readdir, stat.S_IRUSR | stat.S_IXUSR)
        
        with pytest.raises(Exception, match="Can't write"):
            Storage(directory=readdir)
    
    @pytest.mark.skipif(platform.system() == 'Windows', reason="chmod doesn't work on Windows")
    def test_non_creatable_subdirectory(self, temp_basedir):
        """Test instantiation with non-creatable subdirectory"""
        # Skip if running as root
        if hasattr(os, 'getuid') and os.getuid() == 0:
            pytest.skip("Test not applicable when running as root")
        
        readdir = os.path.join(temp_basedir, 'read')
        os.mkdir(readdir)
        os.chmod(readdir, stat.S_IRUSR | stat.S_IXUSR)
        
        with pytest.raises(Exception, match="Can't create"):
            Storage(directory=os.path.join(readdir, 'subdir'))
    
    def test_writable_directory(self, temp_basedir):
        """Test instantiation with writable directory"""
        writedir = os.path.join(temp_basedir, 'write')
        os.mkdir(writedir)
        os.chmod(writedir, stat.S_IRWXU)
        
        storage = Storage(directory=writedir)
        assert storage is not None
    
    def test_creatable_subdirectory(self, temp_basedir):
        """Test instantiation with creatable subdirectory"""
        writedir = os.path.join(temp_basedir, 'write')
        os.mkdir(writedir)
        os.chmod(writedir, stat.S_IRWXU)
        
        subdir_path = os.path.join(writedir, 'subdir')
        storage = Storage(directory=subdir_path)
        
        assert storage is not None
        assert os.path.isdir(subdir_path)
    
    def test_has_no_name(self, temp_basedir):
        """Test has() method without name parameter"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        with pytest.raises(Exception, match="no name parameter"):
            storage.has()
    
    def test_has_nonexistent_content(self, temp_basedir):
        """Test has() for non-existent content"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        assert not storage.has(name='test')
    
    def test_restore_no_name(self, temp_basedir):
        """Test restore() without name parameter"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        with pytest.raises(Exception, match="no name parameter"):
            storage.restore()
    
    def test_restore_nonexistent_content(self, temp_basedir):
        """Test restore() for non-existent content"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        result = storage.restore(name='test')
        assert result is None
    
    def test_save_no_name(self, temp_basedir):
        """Test save() without name parameter"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        with pytest.raises(Exception, match="no name parameter"):
            storage.save(data={'foo': 'bar'})
    
    def test_save_no_data(self, temp_basedir):
        """Test save() without data parameter"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        with pytest.raises(Exception, match="no data parameter"):
            storage.save(name='test')
    
    def test_save_and_restore(self, temp_basedir):
        """Test save and restore cycle"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        test_data = {'foo': 'bar', 'baz': [1, 2, 3]}
        
        storage.save(name='test', data=test_data)
        assert storage.has(name='test')
        
        restored = storage.restore(name='test')
        assert restored == test_data
    
    def test_remove_no_name(self, temp_basedir):
        """Test remove() without name parameter"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        with pytest.raises(Exception, match="no name parameter"):
            storage.remove()
    
    def test_remove_content(self, temp_basedir):
        """Test remove() for existing content"""
        writedir = os.path.join(temp_basedir, 'write')
        os.makedirs(writedir, exist_ok=True)
        storage = Storage(directory=writedir)
        
        # Save some data
        storage.save(name='test', data={'foo': 'bar'})
        assert storage.has(name='test')
        
        # Remove it
        storage.remove(name='test')
        assert not storage.has(name='test')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
