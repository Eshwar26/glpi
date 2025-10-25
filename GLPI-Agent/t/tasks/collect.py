#!/usr/bin/env python3
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'lib'))

try:
    from GLPI.Agent.Logger import Logger
    from GLPI.Agent.Task.Collect import Collect
    from GLPI.Agent.Target.Server import Server
except ImportError:
    Logger = Collect = Server = None


class TestCollect(unittest.TestCase):
    
    def setUp(self):
        if Logger:
            self.logger = Logger(backends=['Fatal'])
        else:
            self.logger = Mock()
            
        self.tempdir = tempfile.mkdtemp()
        
        if Server:
            self.target = Server(
                url='http://localhost/glpi-any',
                logger=self.logger,
                basevardir=self.tempdir
            )
        else:
            self.target = Mock()
            self.target.get_url.return_value = 'http://localhost/glpi-any'

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    def test_collect_initialization(self):
        task = Collect(
            target=self.target,
            logger=Logger(debug=True) if Logger else Mock(),
            config={'jobs': []}
        )
        self.assertIsNotNone(task)

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_no_communication(self, mock_send):
        mock_send.side_effect = Exception('communication error')
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        
        with self.assertRaises(Exception) as ctx:
            task.run()
        self.assertIn('communication error', str(ctx.exception))

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_empty_response(self, mock_send):
        mock_send.return_value = {}
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        
        with self.assertRaises(Exception) as ctx:
            task.run()
        self.assertIn('No job schedule returned', str(ctx.exception))

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_malformed_schedule(self, mock_send):
        mock_send.return_value = {'schedule': {}}
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        
        with self.assertRaises(Exception) as ctx:
            task.run()
        self.assertIn('Malformed schedule', str(ctx.exception))

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_empty_schedule(self, mock_send):
        mock_send.return_value = {'schedule': []}
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        
        with self.assertRaises(Exception) as ctx:
            task.run()
        self.assertIn('No Collect job enabled', str(ctx.exception))

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_bad_schedule(self, mock_send):
        mock_send.return_value = {'schedule': [{}]}
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        
        with self.assertRaises(Exception) as ctx:
            task.run()
        self.assertIn('No Collect job found', str(ctx.exception))

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_normal_schedule(self, mock_send):
        mock_send.return_value = {'schedule': [{'task': 'Collect'}]}
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        task.run()
        
        self.assertTrue(mock_send.called)

    @unittest.skipIf(Collect is None, "Collect task not implemented")
    @patch('GLPI.Agent.HTTP.Client.Fusion.send')
    def test_normal_schedule_with_remote_url(self, mock_send):
        mock_send.return_value = {'schedule': [{'task': 'Collect', 'remote': 'xxx'}]}
        
        task = Collect(target=self.target, logger=self.logger, config={'jobs': []})
        
        with self.assertRaises(Exception) as ctx:
            task.run()
        self.assertIn('Nothing to do', str(ctx.exception))


if __name__ == '__main__':
    unittest.main(verbosity=2)

