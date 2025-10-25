#!/usr/bin/env python3
import sys
import os
import unittest
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'lib'))

try:
    from GLPI.Agent.Task.Deploy import Deploy
except ImportError:
    Deploy = None


class TestDeployValidate(unittest.TestCase):
    
    TESTS = [
        {
            'json': '{"jobs":[[],{"checks":[{"path":"/etc/fstab","type":"filePresent","return":"error"}],"associatedFiles":{"6b620ce663ba13061b480e9897bfa0ef98d039a7747c8286b37a967fb505b12e6e83f10bd0ac1b89a78d4c713a3251fb77ccf0a5cfc890cba43a3627e26ff9b3":{"uncompress":1,"name":"fusioninventory-for-glpi.tar.gz","is_p2p":0,"multiparts":[{"fusioninventory-for-glpi.tar.gz":"04c1ba7f890df17966725eb600fca1a28fb7bdc7573a30869ac2cc78796f6b72ee522276509e7e9350ef2fc9685df0cfc90b5e3546bb0437e661ccec7da97a49"}],"p2p-retention-duration":0}},"actions":{"move":[{"*":"/tmp/input"}]}}]}',
            'ret': None,
            'msg': "missing associatedFiles key",
        },
        {
            'json': '[]',
            'ret': None,
            'msg': "Bad answer from server. Not a hash reference.",
        },
        {
            'json': '',
            'ret': None,
            'msg': "No answer from server.",
        },
        {
            'json': '{"jobs":[{"uuid":"4e4e3bfd87e3b"},{"check":[{"path":"/etc/fstab","type":"filePresent","return":"error"}],"associatedFiles":["6b620ce663ba13061b480e9897bfa0ef98d039a7747c8286b37a967fb505b12e6e83f10bd0ac1b89a78d4c713a3251fb77ccf0a5cfc890cba43a3627e26ff9b3"],"actions":{"move":[{"*":"/tmp/input"}]},"uuid":"4e4e3bfd90cc5"}],"associatedFiles":{"6b620ce663ba13061b480e9897bfa0ef98d039a7747c8286b37a967fb505b12e6e83f10bd0ac1b89a78d4c713a3251fb77ccf0a5cfc890cba43a3627e26ff9b3":{"uncompress":1,"name":"fusioninventory-for-glpi.tar.gz","is_p2p":0,"multiparts":[{"fusioninventory-for-glpi.tar.gz":"04c1ba7f890df17966725eb600fca1a28fb7bdc7573a30869ac2cc78796f6b72ee522276509e7e9350ef2fc9685df0cfc90b5e3546bb0437e661ccec7da97a49"},{"fusioninventory-for-glpi.tar.gz":"04c1ba7f890df17966725eb600fca1a28fb7bdc7573a30869ac2cc78796f6b72ee522276509e7e9350ef2fc9685df0cfc90b5e3546bb0437e661ccec7da97a49"}],"p2p-retention-duration":0}}}',
            'ret': None,
            'msg': "Missing key `mirrors' in associatedFiles"
        },
        {
            'json': '{"jobs":[{"checks":[{"path":"/etc/fstab","type":"filePresent","return":"error"}],"associatedFiles":[],"actions":{"move":[{"*":"/tmp/input"}]},"uuid":"4e4e3bfd90cc5"}],"associatedFiles":{}}',
            'ret': None,
            'msg': "jobs/actions must be an array"
        },
        {
            'json': '{"jobs":[{"checks":[{"path":"/etc/fstab","type":"filePresent","return":"error"}],"associatedFiles":[],"actions":{"move":[{"*":"/tmp/input"}]}}],"associatedFiles":{}}',
            'ret': None,
            'msg': "Missing key `uuid' in jobs"
        },
    ]

    @unittest.skipIf(Deploy is None, "Deploy task not implemented")
    def test_validate_answer(self):
        for test in self.TESTS:
            with self.subTest(msg=test['msg']):
                msg = None
                try:
                    struct = json.loads(test['json']) if test['json'] else None
                except json.JSONDecodeError:
                    struct = None
                
                # Test validation function
                if hasattr(Deploy, 'validate_answer'):
                    ret = Deploy.validate_answer(struct)
                    expected_ret = test['ret'] is not None
                    actual_ret = ret is not None
                    self.assertEqual(actual_ret, expected_ret, f"returned code for {test['msg']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

