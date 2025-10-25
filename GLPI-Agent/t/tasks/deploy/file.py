#!/usr/bin/env python3
import sys
import os
import unittest
import tempfile
import hashlib
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'lib'))

try:
    from GLPI.Agent.Task.Deploy.File import File
except ImportError:
    File = None


class TestDeployFile(unittest.TestCase):
    
    def setUp(self):
        self.datastoredir = tempfile.mkdtemp()
        self.filedir = tempfile.mkdtemp()
        
        # Create test file
        self.test_file = os.path.join(self.filedir, 'toto')
        with open(self.test_file, 'w') as f:
            f.write('foobar\n')
        
        # Calculate SHA512
        sha = hashlib.sha512()
        with open(self.test_file, 'rb') as f:
            sha.update(f.read())
        self.sha512 = sha.hexdigest()

    @unittest.skipIf(File is None, "Deploy File not implemented")
    def test_file_creation(self):
        file = File(
            datastore={'path': self.datastoredir},
            sha512='void',
            data={'multiparts': [self.sha512]}
        )
        self.assertIsNotNone(file)

    @unittest.skipIf(File is None, "Deploy File not implemented")
    def test_get_part_file_path(self):
        file = File(
            datastore={'path': self.datastoredir},
            sha512='void',
            data={'multiparts': [self.sha512]}
        )
        part_file_path = file.get_part_file_path(self.sha512)
        self.assertIsNotNone(part_file_path)

    @unittest.skipIf(File is None, "Deploy File not implemented")
    def test_file_parts_not_exist(self):
        file = File(
            datastore={'path': self.datastoredir},
            sha512='void',
            data={'multiparts': [self.sha512]}
        )
        part_file_path = file.get_part_file_path(self.sha512)
        self.assertFalse(os.path.isfile(part_file_path))
        self.assertFalse(file.file_parts_exists())

    @unittest.skipIf(File is None, "Deploy File not implemented")
    def test_file_parts_exist(self):
        file = File(
            datastore={'path': self.datastoredir},
            sha512='void',
            data={'multiparts': [self.sha512]}
        )
        part_file_path = file.get_part_file_path(self.sha512)
        
        # Create directory and copy file
        os.makedirs(os.path.dirname(part_file_path), exist_ok=True)
        import shutil
        shutil.copy(self.test_file, part_file_path)
        
        self.assertTrue(os.path.isfile(part_file_path))
        self.assertTrue(file.file_parts_exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)

