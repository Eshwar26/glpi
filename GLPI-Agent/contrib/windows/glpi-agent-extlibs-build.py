#!/usr/bin/env python3
"""GLPI Agent External Libraries Build Script"""

import os
import sys
import re
import platform
import subprocess
from pathlib import Path

# Constants
PROVIDED_BY = "Teclib Edition"

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'packaging'))
sys.path.insert(0, 'lib')

try:
    from CustomActionDllBuildJob import build_steps as ca_build_steps
    from CustomCodeSigning import CustomCodeSigning
    from ToolchainBuildJob import toolchain_build_steps
    from GLPI.Agent.version import VERSION, PROVIDER
except ImportError as e:
    print(f"Failed to import required modules: {e}", file=sys.stderr)
    sys.exit(1)

provider = PROVIDER
version = VERSION


def toolchain_builder(arch: str, **params):
    """
    Create toolchain builder application.
    
    Args:
        arch: Architecture ('x86' or 'x64')
        **params: Additional parameters (notest, clean, cadll, codesigning, cpus)
        
    Returns:
        Builder application configuration
    """
    # In a real implementation, this would create Perl::Dist::ToolChain object
    # For Python, this would be adapted to a Python build framework
    app_config = {
        '_provided_by': PROVIDED_BY,
        '_no_test': params.get('notest', False),
        '_clean': params.get('clean', False),
        'arch': arch,
        '_dllsuffix': '_' if arch == "x86" else '__',
        '_cpus': params.get('cpus', 0),
        '_cadll': params.get('cadll', False),
        'codesigning': params.get('codesigning', False),
        'image_dir': f"C:\\Strawberry-perl-for-{provider}-Agent_build\\build" if params.get('cadll') else f"C:\\Strawberry-perl-for-{provider}-Agent",
        'working_dir': f"C:\\Strawberry-perl-for-{provider}-Agent_build",
        'nointeractive': True,
        'norestorepoints': True,
    }
    
    return app_config


# Parse command line arguments
do_archs = {}
args = {
    'no_test': False,
    'clean': False,
    'cadll': False,
    'codesigning': False,
    'cpus': 0,
}

argv = sys.argv[1:]
i = 0
while i < len(argv):
    arg = argv[i]
    if arg == "--arch":
        i += 1
        if i < len(argv):
            arch = argv[i]
            if re.match(r'^x(86|64)$', arch):
                do_archs[arch] = 32 if arch == "x86" else 64
    elif arg == "--all":
        do_archs = {'x86': 32, 'x64': 64}
    elif arg == "--no-test":
        args['no_test'] = True
    elif arg == "--clean":
        args['clean'] = True
    elif arg == "--cadll":
        args['cadll'] = True
    elif arg.startswith("--code-signing="):
        value = arg.split('=', 1)[1]
        args['codesigning'] = bool(re.match(r'^yes|1$', value, re.IGNORECASE))
    else:
        print(f"Unsupported option: {arg}\n", file=sys.stderr)
    i += 1

# Still select a default arch if none has been selected
if not do_archs:
    do_archs['x64'] = 64

if 'x86' in do_archs:
    print("32 bits toolchain build not supported\n", file=sys.stderr)
    sys.exit(1)

# Get CPU count
try:
    if platform.system() == 'Windows':
        result = subprocess.run(['wmic', 'cpu', 'get', 'NumberOfCores'], 
                              capture_output=True, text=True)
        for line in result.stdout.splitlines():
            match = re.match(r'^(\d+)', line.strip())
            if match:
                count = int(match.group(1))
                if count > 1:
                    args['cpus'] = count
                break
except Exception:
    pass

for arch in sorted(do_archs.keys()):
    if args['cadll']:
        print(f"Building {arch} ca.dll for {provider}-Agent {version} MSI installer CustomAction...\n")
    else:
        print(f"Building {arch} toolchain packages for {provider}-Agent {version}...\n")
    
    builder = toolchain_builder(arch, **args)
    # builder.do_job() would be called here
    debug_dir = builder.get('debug_dir', '')
    final_file = os.path.join(debug_dir, 'global_dump_FINAL.txt') if debug_dir else ''
    if not os.path.exists(final_file):
        sys.exit(1)

print("All toolchain packages building processing passed\n")
sys.exit(0)

