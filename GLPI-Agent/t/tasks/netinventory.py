#!/usr/bin/env python3
import sys
import os
import unittest
from unittest.mock import Mock, patch
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'lib'))

try:
    from GLPI.Agent.Logger import Logger
    from GLPI.Agent.Task.NetInventory import NetInventory
    from GLPI.Agent.Target.Server import Server
    from GLPI.Agent.Config import Config
except ImportError:
    Logger = NetInventory = Server = Config = None


class TestNetInventory(unittest.TestCase):
    
    def setUp(self):
        if Logger:
            self.logger = Logger(backends=['Test'], debug=True)
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

    @unittest.skipIf(NetInventory is None, "NetInventory task not implemented")
    def test_netinventory_initialization(self):
        config = Config() if Config else {}
        task = NetInventory(
            target=self.target,
            logger=self.logger,
            config=config,
            datadir=self.tempdir,
            deviceid='test-case'
        )
        self.assertIsNotNone(task)

    @unittest.skipIf(NetInventory is None, "NetInventory task not implemented")
    @patch('GLPI.Agent.HTTP.Client.OCS.send')
    def test_no_netinventory_case(self, mock_send):
        mock_send.return_value = Mock()
        mock_send.return_value.getOptionsInfoByName.return_value = None
        
        config = Config() if Config else {}
        task = NetInventory(
            target=self.target,
            logger=self.logger,
            config=config,
            datadir=self.tempdir,
            deviceid='no_netinventory_case'
        )
        
        # Should not run when netinventory not requested
        task.run()

    @unittest.skipIf(NetInventory is None, "NetInventory task not implemented")
    @patch('GLPI.Agent.HTTP.Client.OCS.send')
    def test_netinventory_without_device(self, mock_send):
        response = Mock()
        response.getOptionsInfoByName.return_value = {
            'PARAM': {'THREADS_DISCOVERY': '20', 'TIMEOUT': '0'},
            'AUTHENTICATION': [{'ID': '1', 'VERSION': '1', 'COMMUNITY': 'public'}]
        }
        mock_send.return_value = response
        
        config = Config() if Config else {}
        task = NetInventory(
            target=self.target,
            logger=self.logger,
            config=config,
            datadir=self.tempdir,
            deviceid='netinventory_without_device_case'
        )
        
        # Should abort without devices
        task.run()


if __name__ == '__main__':
    unittest.main(verbosity=2)

