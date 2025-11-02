#!/usr/bin/env python3
"""GLPI Agent Built Perl Tests Script"""

import os
import sys
import re
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'packaging'))
sys.path.insert(0, 'lib')

try:
    from PerlBuildJob import PERL_BUILD_STEPS
    from GLPI.Agent.version import PROVIDER
except ImportError as e:
    print(f"Failed to import required modules: {e}", file=sys.stderr)
    sys.exit(1)

provider = PROVIDER

# HACK: make "use Perl::Dist::GLPI::Agent::Step::XXX" works as included plugin
# This would be handled by the build system


def build_app(arch: str):
    """
    Build application for testing.
    
    Args:
        arch: Architecture ('x86' or 'x64')
        
    Returns:
        Build application configuration
    """
    # In a real implementation, this would create Perl::Dist::GLPI::Agent object
    app_config = {
        'arch': arch,
        '_restore_step': PERL_BUILD_STEPS,
        'image_dir': f"C:\\Strawberry-perl-for-{provider}-Agent",
        'working_dir': f"C:\\Strawberry-perl-for-{provider}-Agent_build",
        'nointeractive': True,
        'restorepoints': True,
    }
    
    return app_config


# Parse command line arguments
do_archs = {}

argv = sys.argv[1:]
i = 0
while i < len(argv):
    arg = argv[i]
    if arg == "--arch":
        i += 1
        if i < len(argv):
            arch = argv[i]
            if re.match(r'^x(86|64)$', arch):
                do_archs[arch] = True
    elif arg == "--all":
        do_archs = {
            # 'x86': 32,  # commented out
            'x64': 64
        }
    i += 1

# Default to x64 if none specified
if not do_archs:
    do_archs = ['x64']

for arch in do_archs if isinstance(do_archs, list) else do_archs.keys():
    print(f"Running {arch} built perl tests...\n")
    app = build_app(arch)
    # app.do_job() would be called here
    debug_dir = app.get('debug_dir', '')
    final_file = os.path.join(debug_dir, 'global_dump_FINAL.txt') if debug_dir else ''
    if not os.path.exists(final_file):
        sys.exit(1)

print("Tests processing passed\n")
sys.exit(0)

