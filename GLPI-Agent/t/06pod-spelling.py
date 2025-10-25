#!/usr/bin/env python3

import os
import pytest

# Skip test if not running author tests
if not os.environ.get('TEST_AUTHOR'):
    pytest.skip("Author test, set TEST_AUTHOR environment variable to run", allow_module_level=True)


def test_spelling_in_docs():
    """Test spelling in documentation"""
    # POD spelling check is Perl-specific
    # Python equivalent would use tools like pyspelling
    pytest.skip("POD spelling check is Perl-specific")
