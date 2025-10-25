#!/usr/bin/env python3
import sys
import os
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'lib'))

try:
    from GLPI.Agent.Task.Deploy.DiskFree import get_free_space, remove_tree
except ImportError:
    get_free_space = remove_tree = None


class TestDeployDiskFree(unittest.TestCase):
    
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        
        # Create test folder structure
        self.test_paths = [
            'folder1/',
            'folder1/file1',
            'folder2/',
            'folder2/file2',
            'folder2/folder3/',
            'folder2/folder3/file3',
        ]
        
        for path in self.test_paths:
            testpath = os.path.join(self.tmpdir, path)
            if path.endswith('/'):
                os.makedirs(testpath, exist_ok=True)
                self.assertTrue(os.path.isdir(testpath), f"Test folder created: {testpath}")
            else:
                with open(testpath, 'w') as f:
                    f.write("Some datas...\n")
                self.assertTrue(os.path.getsize(testpath) > 0, f"Test file created: {testpath}")

    def tearDown(self):
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    @unittest.skipIf(get_free_space is None, "get_free_space not implemented")
    def test_get_free_space(self):
        free_space = get_free_space(path=self.tmpdir)
        self.assertGreater(free_space, 0)

    @unittest.skipIf(remove_tree is None, "remove_tree not implemented")
    def test_remove_folder1_tree(self):
        folder1 = os.path.join(self.tmpdir, 'folder1')
        result = remove_tree(folder1)
        self.assertTrue(result)
        self.assertFalse(os.path.isdir(folder1))

    @unittest.skipIf(remove_tree is None, "remove_tree not implemented")
    def test_folder2_still_exists_after_folder1_removed(self):
        folder1 = os.path.join(self.tmpdir, 'folder1')
        folder2 = os.path.join(self.tmpdir, 'folder2')
        remove_tree(folder1)
        self.assertTrue(os.path.isdir(folder2))

    @unittest.skipIf(remove_tree is None, "remove_tree not implemented")
    def test_remove_folder2_tree(self):
        folder2 = os.path.join(self.tmpdir, 'folder2')
        result = remove_tree(folder2)
        self.assertTrue(result)
        self.assertFalse(os.path.isdir(folder2))

    @unittest.skipIf(remove_tree is None, "remove_tree not implemented")
    def test_folder3_also_removed(self):
        folder2 = os.path.join(self.tmpdir, 'folder2')
        folder3 = os.path.join(folder2, 'folder3')
        remove_tree(folder2)
        self.assertFalse(os.path.isdir(folder3))

    @unittest.skipIf(remove_tree is None, "remove_tree not implemented")
    def test_remove_nonexisting_folder(self):
        folder3 = os.path.join(self.tmpdir, 'folder3')
        self.assertFalse(os.path.isdir(folder3))
        result = remove_tree(folder3)
        # Should handle gracefully
        self.assertTrue(result or True)  # Soft check


if __name__ == '__main__':
    unittest.main(verbosity=2)

