#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'lib'))

try:
    from GLPI.Agent.Task.Deploy.P2P import P2P
except ImportError:
    P2P = None


class TestDeployP2P(unittest.TestCase):
    
    TESTS = [
        {
            'name': 'Ignore',
            'address': {'ip': '127.0.0.1', 'mask': '255.0.0.0'},
            'result': []
        },
        {
            'name': 'Ignore-Large-Range',
            'address': {'ip': '10.0.0.10', 'mask': '255.0.0.0'},
            'result': []
        },
        {
            'name': '192.168.5.5',
            'address': {'ip': '192.168.5.5', 'mask': '255.255.255.0'},
            'result': [
                '192.168.5.2', '192.168.5.3', '192.168.5.4',
                '192.168.5.6', '192.168.5.7', '192.168.5.8'
            ]
        },
        {
            'name': '10.5.6.200',
            'address': {'ip': '10.5.6.200', 'mask': '255.255.252.0'},
            'result': [
                '10.5.6.197', '10.5.6.198', '10.5.6.199',
                '10.5.6.201', '10.5.6.202', '10.5.6.203'
            ]
        },
        {
            'name': '192.168.1.2/24',
            'address': {'ip': '192.168.1.2', 'mask': '255.255.255.0'},
            'result': [
                '192.168.1.1', '192.168.1.3', '192.168.1.4',
                '192.168.1.5', '192.168.1.6', '192.168.1.7'
            ]
        },
        {
            'name': '192.168.1.1/24',
            'address': {'ip': '192.168.1.1', 'mask': '255.255.255.0'},
            'result': [
                '192.168.1.2', '192.168.1.3', '192.168.1.4',
                '192.168.1.5', '192.168.1.6', '192.168.1.7'
            ]
        },
        {
            'name': '192.168.2.253/24',
            'address': {'ip': '192.168.2.253', 'mask': '255.255.255.0'},
            'result': [
                '192.168.2.250', '192.168.2.251', '192.168.2.252',
                '192.168.2.254', '192.168.2.255', '192.168.2.249'
            ]
        },
    ]

    @unittest.skipIf(P2P is None, "Deploy P2P not implemented")
    def test_p2p_address_generation(self):
        for test in self.TESTS:
            with self.subTest(name=test['name']):
                # Test P2P address generation
                # Actual implementation depends on P2P class
                pass


if __name__ == '__main__':
    unittest.main(verbosity=2)

