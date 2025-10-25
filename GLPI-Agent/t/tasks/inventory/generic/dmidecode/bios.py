#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..', 'lib'))

try:
    from GLPI.Agent.Task.Inventory.Generic.Dmidecode.Bios import Bios
except ImportError:
    Bios = None


class TestDmidecodeBios(unittest.TestCase):
    
    TESTS = {
        'freebsd-6.2': {
            'MMANUFACTURER': None,
            'SSN': None,
            'SKUNUMBER': None,
            'ASSETTAG': None,
            'BMANUFACTURER': None,
            'MSN': None,
            'SMODEL': None,
            'SMANUFACTURER': None,
            'BDATE': None,
            'MMODEL': 'CN700-8237R',
            'BVERSION': None
        },
        'freebsd-8.1': {
            'MMANUFACTURER': 'Hewlett-Packard',
            'SSN': 'CNF01207X6',
            'SKUNUMBER': 'WA017EA#ABF',
            'ASSETTAG': None,
            'BMANUFACTURER': 'Hewlett-Packard',
            'MSN': 'CNF01207X6',
            'SMODEL': 'HP Pavilion dv6 Notebook PC',
            'SMANUFACTURER': 'Hewlett-Packard',
            'BDATE': '05/17/2010',
            'MMODEL': '3659',
            'BVERSION': 'F.1C'
        },
        'linux-1': {
            'MMANUFACTURER': 'ASUSTeK Computer INC.',
            'SSN': None,
            'SKUNUMBER': None,
            'ASSETTAG': 'Asset-1234567890',
            'BMANUFACTURER': 'American Megatrends Inc.',
            'MSN': 'MS1C93BB0H00980',
            'SMODEL': None,
            'SMANUFACTURER': None,
            'BDATE': '04/07/2009',
            'MMODEL': 'P5Q',
            'BVERSION': '2102'
        },
    }

    @unittest.skipIf(Bios is None, "Dmidecode Bios module not implemented")
    def test_bios_parsing(self):
        for test_name, expected in self.TESTS.items():
            with self.subTest(test=test_name):
                dmidecode_file = os.path.join(
                    os.path.dirname(__file__), 
                    '..', '..', '..', '..', '..', 
                    'resources', 'generic', 'dmidecode', test_name
                )
                
                if os.path.exists(dmidecode_file):
                    # Parse dmidecode output and validate
                    result = Bios.parse(file=dmidecode_file)
                    
                    for key, value in expected.items():
                        self.assertEqual(result.get(key), value,
                            f"{test_name}: {key} mismatch")


if __name__ == '__main__':
    unittest.main(verbosity=2)

