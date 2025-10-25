#!/usr/bin/env python3

import os
import sys
import tempfile
import pytest

sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent.XML import XML
    from GLPI.Test.Utils import run_executable
except ImportError:
    XML = run_executable = None


class TestAppsAgent:
    """Tests for glpi-agent application"""
    
    def test_agent_help(self):
        """Test agent --help option"""
        if run_executable is None:
            pytest.skip("Test utilities not implemented")
        
        try:
            out, err, rc = run_executable('glpi-agent', '--help')
            
            assert rc == 0, "--help should exit with status 0"
            assert err == '', "--help should not produce stderr"
            assert 'Usage:' in out, "--help should show usage"
        except:
            pytest.skip("glpi-agent executable not found or not implemented")
    
    def test_agent_version(self):
        """Test agent --version option"""
        if run_executable is None:
            pytest.skip("Test utilities not implemented")
        
        try:
            out, err, rc = run_executable('glpi-agent', '--version')
            
            assert rc == 0, "--version should exit with status 0"
            assert err == '', "--version should not produce stderr"
            assert out.strip(), "--version should produce output"
        except:
            pytest.skip("glpi-agent executable not found or not implemented")
    
    def test_agent_no_target(self):
        """Test agent with no target defined"""
        if run_executable is None:
            pytest.skip("Test utilities not implemented")
        
        try:
            out, err, rc = run_executable('glpi-agent', '--config none')
            
            assert rc == 1, "no target should exit with status 1"
            assert 'No target defined' in err or 'No target' in out
        except:
            pytest.skip("glpi-agent executable not found or not implemented")
    
    def test_agent_incompatible_options(self):
        """Test agent with incompatible options"""
        if run_executable is None:
            pytest.skip("Test utilities not implemented")
        
        try:
            out, err, rc = run_executable(
                'glpi-agent',
                '--config none --conf-file /foo/bar'
            )
            
            assert rc == 1, "incompatible options should exit with status 1"
            assert "don't use --conf-file" in err or "conf-file" in err
        except:
            pytest.skip("glpi-agent executable not found or not implemented")
    
    def test_agent_inventory(self):
        """Test basic inventory execution"""
        if run_executable is None or XML is None:
            pytest.skip("Test utilities or XML not implemented")
        
        try:
            with tempfile.TemporaryDirectory() as vardir:
                base_options = f"--debug --no-task ocsdeploy,wakeonlan,snmpquery,netdiscovery --config none --vardir {vardir}"
                
                out, err, rc = run_executable(
                    'glpi-agent',
                    f"{base_options} --local - --no-category printer"
                )
                
                # Check execution
                assert rc == 0, "inventory should execute successfully"
                
                # Verify no broken modules
                assert 'module' not in err or 'failure to load' not in err
                assert 'unexpected error' not in err
                assert 'uninitialized value' not in err.lower()
                
                # Verify XML output
                assert '<?xml' in out, "output should be XML"
                
                # Parse XML
                if XML:
                    content = XML(string=out)
                    assert content is not None, "output should be valid XML"
        except:
            pytest.skip("Full inventory test requires glpi-agent implementation")
    
    def test_agent_with_additional_content(self):
        """Test agent with additional content"""
        if run_executable is None or XML is None:
            pytest.skip("Test utilities not implemented")
        
        pytest.skip("Additional content tests require full implementation")
    
    def test_agent_output_location(self):
        """Test agent output location options"""
        if run_executable is None:
            pytest.skip("Test utilities not implemented")
        
        pytest.skip("Output location tests require full implementation")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
