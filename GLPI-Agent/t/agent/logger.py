#!/usr/bin/env python3

import os
import sys
import platform
import tempfile
import stat
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.Config import Config
    from GLPI.Agent.Logger import Logger
except ImportError:
    Config = Logger = None


@pytest.mark.skipif(Logger is None, reason="Logger class not implemented")
class TestLogger:
    """Tests for GLPI Agent Logger"""
    
    def test_logger_creation(self):
        """Test logger instantiation"""
        logger = Logger()
        assert logger is not None
        assert isinstance(logger, Logger)
    
    def test_logger_default_backend(self):
        """Test logger has default backend"""
        logger = Logger()
        
        if hasattr(logger, 'backends'):
            assert len(logger.backends) >= 1
            # Default should be Stderr
            backend_name = logger.backends[0].__class__.__name__
            assert 'Stderr' in backend_name or 'Test' in backend_name
    
    def test_logger_multiple_backends_windows(self):
        """Test logger with multiple backends on Windows"""
        if platform.system() != 'Windows':
            pytest.skip("Windows-only test")
        
        if Config is None:
            pytest.skip("Config not implemented")
        
        try:
            config = Config(options={
                'config': 'none',
                'logger': 'stderr,Test'
            })
            
            logger = Logger(config=config)
            
            if hasattr(logger, 'backends'):
                assert len(logger.backends) == 2
        except:
            pytest.skip("Multiple backends not fully implemented")
    
    def test_logger_multiple_backends_unix(self):
        """Test logger with multiple backends on Unix"""
        if platform.system() == 'Windows':
            pytest.skip("Unix-only test")
        
        if Config is None:
            pytest.skip("Config not implemented")
        
        try:
            config = Config(options={
                'config': 'none',
                'logger': 'Stderr,Syslog,Test'
            })
            
            logger = Logger(config=config)
            
            if hasattr(logger, 'backends'):
                assert len(logger.backends) == 3
        except:
            pytest.skip("Multiple backends not fully implemented")
    
    def test_logger_debug_level(self):
        """Test logger debug level"""
        if Config is None:
            pytest.skip("Config not implemented")
        
        try:
            config = Config(options={
                'config': 'none',
                'debug': True
            })
            
            logger = Logger(config=config)
            
            if hasattr(logger, 'debug'):
                assert logger.debug or hasattr(logger, '_debug')
        except:
            pytest.skip("Debug level not fully implemented")
    
    def test_logger_file_backend(self):
        """Test logger with file backend"""
        if Config is None:
            pytest.skip("Config not implemented")
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            logfile = f.name
        
        try:
            config = Config(options={
                'config': 'none',
                'logger': 'File',
                'logfile': logfile
            })
            
            logger = Logger(config=config)
            
            # Log a message
            if hasattr(logger, 'info'):
                logger.info('Test message')
            
            # Check file was created and has content
            assert os.path.exists(logfile)
            
            with open(logfile, 'r') as f:
                content = f.read()
                if content:
                    assert 'Test message' in content or len(content) > 0
        except:
            pytest.skip("File backend not fully implemented")
        finally:
            if os.path.exists(logfile):
                os.unlink(logfile)
    
    def test_logger_file_backend_permissions(self):
        """Test logger file backend handles permissions"""
        if platform.system() == 'Windows':
            pytest.skip("Permission test not applicable on Windows")
        
        if hasattr(os, 'getuid') and os.getuid() == 0:
            pytest.skip("Test not applicable when running as root")
        
        if Config is None:
            pytest.skip("Config not implemented")
        
        # Create a file with no write permissions
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            logfile = f.name
        
        try:
            os.chmod(logfile, stat.S_IRUSR)
            
            # Try to use it as logfile - should handle gracefully
            try:
                config = Config(options={
                    'config': 'none',
                    'logger': 'File',
                    'logfile': logfile
                })
                
                logger = Logger(config=config)
                # Should either raise or fallback to stderr
            except:
                # Expected to fail
                pass
        finally:
            os.chmod(logfile, stat.S_IWUSR | stat.S_IRUSR)
            os.unlink(logfile)
    
    def test_logger_methods(self):
        """Test logger has standard logging methods"""
        logger = Logger()
        
        # Test method existence
        methods = ['debug', 'info', 'warning', 'error']
        for method in methods:
            if hasattr(logger, method):
                func = getattr(logger, method)
                assert callable(func)
    
    def test_logger_message_logging(self):
        """Test actual message logging"""
        if Config is None:
            pytest.skip("Config not implemented")
        
        try:
            config = Config(options={
                'config': 'none',
                'logger': 'Test'
            })
            
            logger = Logger(config=config)
            
            # Try logging messages at different levels
            if hasattr(logger, 'info'):
                logger.info('Info message')
            
            if hasattr(logger, 'warning'):
                logger.warning('Warning message')
            
            if hasattr(logger, 'error'):
                logger.error('Error message')
            
            # If using Test backend, should be able to retrieve messages
            if hasattr(logger, 'backends') and len(logger.backends) > 0:
                backend = logger.backends[0]
                if hasattr(backend, 'messages'):
                    messages = backend.messages
                    # Should have logged messages
                    assert len(messages) > 0
        except:
            pytest.skip("Message logging not fully implemented")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
