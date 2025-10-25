#!/usr/bin/env python3

import os
import pytest

# Skip test if not running author tests
if not os.environ.get('TEST_AUTHOR'):
    pytest.skip("Author test, set TEST_AUTHOR environment variable to run", allow_module_level=True)


def test_no_broken_links():
    """Test that documentation has no broken links"""
    # POD::No404s is Perl-specific for checking links in POD
    # Python equivalent would check links in docstrings/documentation
    pytest.skip("POD link checking is Perl-specific")
