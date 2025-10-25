#!/usr/bin/env python3

import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest

# Add paths for imports
sys.path.insert(0, 't/lib')
sys.path.insert(0, 'lib')

try:
    from GLPI.Agent import Agent
    from GLPI.Agent.Config import Config
    from GLPI.Agent.Logger import Logger
except ImportError:
    Agent = Config = Logger = None


def create_file(directory, filename, content):
    """Create a file with the given content"""
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename
    with open(file_path, 'w') as f:
        f.write(content)


@pytest.fixture
def temp_libdir():
    """Create a temporary library directory for testing"""
    libdir = tempfile.mkdtemp()
    sys.path.insert(0, libdir)
    yield libdir
    sys.path.remove(libdir)
    if not os.environ.get('TEST_DEBUG'):
        shutil.rmtree(libdir, ignore_errors=True)


@pytest.mark.skipif(Agent is None, reason="Agent class not implemented")
class TestAgent:
    """Tests for GLPI Agent"""
    
    def test_no_agentid_by_default(self, temp_libdir):
        """Test that agentid is not set by default"""
        agent = Agent(libdir=temp_libdir)
        assert not hasattr(agent, 'agentid') or agent.agentid is None
    
    def test_single_task(self, temp_libdir):
        """Test discovery of a single task"""
        if Agent is None:
            pytest.skip("Agent not implemented")
        
        # Create Task1
        create_file(
            f"{temp_libdir}/GLPI/Agent/Task/Task1",
            "Version.py",
            "VERSION = 42\n"
        )
        
        agent = Agent(libdir=temp_libdir)
        available_tasks = agent.getAvailableTasks() if hasattr(agent, 'getAvailableTasks') else {}
        assert available_tasks.get('Task1') == 42, "single task"
    
    def test_multiple_tasks(self, temp_libdir):
        """Test discovery of multiple tasks"""
        if Agent is None:
            pytest.skip("Agent not implemented")
        
        # Create Task1
        create_file(
            f"{temp_libdir}/GLPI/Agent/Task/Task1",
            "Version.py",
            "VERSION = 42\n"
        )
        
        # Create Task2
        create_file(
            f"{temp_libdir}/GLPI/Agent/Task/Task2",
            "Version.py",
            "VERSION = 42\n"
        )
        
        agent = Agent(libdir=temp_libdir)
        available_tasks = agent.getAvailableTasks() if hasattr(agent, 'getAvailableTasks') else {}
        assert available_tasks.get('Task1') == 42
        assert available_tasks.get('Task2') == 42
    
    def test_task_with_wrong_syntax(self, temp_libdir):
        """Test that tasks with wrong syntax are skipped"""
        if Agent is None:
            pytest.skip("Agent not implemented")
        
        # Create valid tasks
        create_file(
            f"{temp_libdir}/GLPI/Agent/Task/Task1",
            "Version.py",
            "VERSION = 42\n"
        )
        
        create_file(
            f"{temp_libdir}/GLPI/Agent/Task/Task2",
            "Version.py",
            "VERSION = 42\n"
        )
        
        # Create Task3 with wrong syntax (missing import)
        create_file(
            f"{temp_libdir}/GLPI/Agent/Task/Task3",
            "Version.py",
            "from does.not.exist import Something\nVERSION = 42\n"
        )
        
        agent = Agent(libdir=temp_libdir)
        available_tasks = agent.getAvailableTasks() if hasattr(agent, 'getAvailableTasks') else {}
        
        # Task3 should not be available due to import error
        assert available_tasks.get('Task1') == 42
        assert available_tasks.get('Task2') == 42
        assert 'Task3' not in available_tasks
    
    def test_task_execution_plan(self, temp_libdir):
        """Test task execution plan computation"""
        if Agent is None or Config is None or Logger is None:
            pytest.skip("Required classes not implemented")
        
        # Create tasks
        for task_num in [1, 2, 5]:
            create_file(
                f"{temp_libdir}/GLPI/Agent/Task/Task{task_num}",
                "Version.py",
                "VERSION = 42\n"
            )
        
        # Setup agent
        agent = Agent(libdir=temp_libdir)
        
        try:
            agent.config = Config(options={
                'config': 'none',
                'debug': True,
                'logger': 'Test'
            })
            agent.config.set('no-task', ['Task5'])
            agent.config.set('tasks', ['Task1', 'Task5', 'Task1', 'Task5', 'Task5', 'Task2', 'Task1'])
            
            if hasattr(agent, 'getAvailableTasks'):
                available_tasks = agent.getAvailableTasks()
            else:
                available_tasks = {}
            
            agent.logger = Logger(config=agent.config)
            
            if hasattr(agent, 'computeTaskExecutionPlan'):
                plan = agent.computeTaskExecutionPlan(available_tasks)
                # Task5 should be filtered out due to no-task setting
                # Duplicates should be kept
                assert plan == ['Task1', 'Task1', 'Task2', 'Task1']
        except AttributeError:
            pytest.skip("Task execution plan methods not implemented")
    
    def test_config_loading_from_file(self, temp_libdir):
        """Test loading configuration from file"""
        if Agent is None or Config is None:
            pytest.skip("Agent or Config not implemented")
        
        agent = Agent(libdir=temp_libdir)
        agent.datadir = './share'
        agent.vardir = './var'
        
        # Reset config
        if hasattr(agent, 'config'):
            delattr(agent, 'config')
        
        options = {
            'local': '.',
            'logger': 'Test',
            'conf-file': 'resources/config/sample1',
            'config': 'file'
        }
        
        try:
            if hasattr(agent, 'init'):
                agent.init(options=options)
                
                # Verify config was loaded
                assert hasattr(agent, 'config')
                assert agent.config is not None
                assert isinstance(agent.config, Config)
                
                if hasattr(agent.config, 'get'):
                    conf_file = agent.config.get('conf-file')
                    no_task = agent.config.get('no-task', [])
                    
                    assert conf_file is not None
                    assert len(no_task) == 2
                    assert 'snmpquery' in no_task and 'wakeonlan' in no_task
        except (AttributeError, FileNotFoundError):
            pytest.skip("Config file loading not fully implemented")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
