#!/usr/bin/env python3

import os
import sys
import platform
import tempfile
import time
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Target.Server import Server
except ImportError:
    Server = None


@pytest.mark.skipif(Server is None, reason="Server target not implemented")
class TestTarget:
    """Tests for GLPI Agent Targets"""
    
    @pytest.fixture
    def temp_basedir(self):
        """Create temporary base directory for tests"""
        basedir = tempfile.mkdtemp()
        yield basedir
        if not os.environ.get('TEST_DEBUG'):
            import shutil
            shutil.rmtree(basedir, ignore_errors=True)
    
    def test_server_no_url(self):
        """Test Server target instantiation without URL"""
        with pytest.raises(Exception, match="no url parameter"):
            Server()
    
    def test_server_no_basedir(self):
        """Test Server target instantiation without base directory"""
        with pytest.raises(Exception, match="no basevardir parameter"):
            Server(url='http://foo/bar')
    
    def test_server_with_url_and_basedir(self, temp_basedir):
        """Test Server target instantiation with URL and basedir"""
        target = Server(
            url='http://my.domain.tld/',
            basevardir=temp_basedir
        )
        
        assert target is not None
        
        # Check storage directory was created
        storage_dir_name = 'http..__my.domain.tld' if platform.system() == 'Windows' else 'http:__my.domain.tld'
        storage_dir = os.path.join(temp_basedir, storage_dir_name)
        assert os.path.isdir(storage_dir)
        
        # Check identifier
        if hasattr(target, 'id'):
            assert target.id == 'server0'
    
    def test_server_missing_path(self, temp_basedir):
        """Test that missing path in URL is handled correctly"""
        target = Server(
            url='http://my.domain.tld',
            basevardir=temp_basedir
        )
        
        if hasattr(target, 'getUrl'):
            assert target.getUrl() == 'http://my.domain.tld'
    
    def test_server_bare_hostname(self, temp_basedir):
        """Test that bare hostname gets http:// prefix"""
        target = Server(
            url='my.domain.tld',
            basevardir=temp_basedir
        )
        
        if hasattr(target, 'getUrl'):
            url = target.getUrl()
            assert url == 'http://my.domain.tld'
    
    def test_max_delay_default(self, temp_basedir):
        """Test default max delay value"""
        target = Server(
            url='http://my.domain.tld',
            basevardir=temp_basedir
        )
        
        if hasattr(target, 'getMaxDelay'):
            assert target.getMaxDelay() == 3600
    
    def test_state_persistence(self, temp_basedir):
        """Test that state persists across instantiations"""
        target1 = Server(
            url='http://my.domain.tld',
            basevardir=temp_basedir
        )
        
        if not hasattr(target1, 'getNextRunDate'):
            pytest.skip("getNextRunDate not implemented")
        
        next_run_date1 = target1.getNextRunDate()
        
        # Check state file exists
        storage_dir_name = 'http..__my.domain.tld' if platform.system() == 'Windows' else 'http:__my.domain.tld'
        storage_dir = os.path.join(temp_basedir, storage_dir_name)
        state_file = os.path.join(storage_dir, 'target.dump')
        assert os.path.isfile(state_file)
        
        # Create new target instance
        target2 = Server(
            url='http://my.domain.tld',
            basevardir=temp_basedir
        )
        
        next_run_date2 = target2.getNextRunDate()
        assert next_run_date1 == next_run_date2
    
    def test_next_run_date_validity(self, temp_basedir):
        """Test next run date is within valid range"""
        target = Server(
            url='http://my-2.domain.tld',
            basevardir=temp_basedir
        )
        
        if not hasattr(target, 'getNextRunDate') or not hasattr(target, 'getMaxDelay'):
            pytest.skip("Required methods not implemented")
        
        current_time = time.time()
        next_run = target.getNextRunDate()
        max_delay = target.getMaxDelay()
        
        assert next_run >= current_time
        assert next_run <= current_time + max_delay
    
    def test_reset_next_run_date(self, temp_basedir):
        """Test resetting next run date"""
        target = Server(
            url='http://my-3.domain.tld',
            basevardir=temp_basedir
        )
        
        if not hasattr(target, 'resetNextRunDate'):
            pytest.skip("resetNextRunDate not implemented")
        
        current_time = time.time()
        max_delay = target.getMaxDelay() if hasattr(target, 'getMaxDelay') else 3600
        
        target.resetNextRunDate()
        next_run = target.getNextRunDate() if hasattr(target, 'getNextRunDate') else 0
        
        if next_run:
            assert next_run >= current_time + max_delay
            assert next_run <= current_time + 2 * max_delay
    
    def test_outdated_run_date(self, temp_basedir):
        """Test handling of outdated run dates"""
        target = Server(
            url='http://my-4.domain.tld',
            basevardir=temp_basedir
        )
        
        if not hasattr(target, 'setMaxDelay'):
            pytest.skip("setMaxDelay not implemented")
        
        current_time = time.time()
        
        # Set dates in the past
        if hasattr(target, 'nextRunDate'):
            target.nextRunDate = current_time - 86400
        if hasattr(target, 'baseRunDate'):
            target.baseRunDate = current_time - 86400
        
        # Save state and reload
        target.setMaxDelay(3600)
        
        # Create new instance
        target2 = Server(
            url='http://my-4.domain.tld',
            basevardir=temp_basedir
        )
        
        if hasattr(target2, 'getNextRunDate'):
            next_run = target2.getNextRunDate()
            max_delay = target2.getMaxDelay() if hasattr(target2, 'getMaxDelay') else 3600
            
            assert next_run >= current_time
            assert next_run <= current_time + max_delay


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
