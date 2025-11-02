#!/usr/bin/env python3
"""CustomActionDllBuildJob - Custom Action DLL build job configuration"""

import time
from typing import Dict, Any
from .ToolchainBuildJob import TOOLCHAIN_ARCHIVE


def build_steps(arch: str) -> Dict[str, Any]:
    """
    Get custom action DLL build steps configuration.
    
    Args:
        arch: Architecture ('x86' or 'x64')
        
    Returns:
        Dictionary with build job configuration
    """
    # Generate version from current time
    now = time.gmtime()
    version = f"{now.tm_year % 100}.{now.tm_mon}.{now.tm_mday}.{now.tm_hour}"
    
    bits = 64 if arch == 'x64' else 32
    
    return {
        'app_simplename': "ca.dll",
        'app_version': version,
        'bits': bits,
        'build_job_steps': [
            # STEP 0: Binaries downloads
            {
                'plugin': 'Perl::Dist::Strawberry::Step::ToolChain',
                'packages': [
                    {
                        'name': 'winlibs-x86_64',
                        'file': TOOLCHAIN_ARCHIVE,
                        'not_if_file': 'mingw64/bin/gcc.exe',
                    },
                ],
            },
            # STEP 1: Binaries cleanup
            {
                'plugin': 'Perl::Dist::Strawberry::Step::FilesAndDirs',
                'commands': [
                    {'do': 'removefile_recursive', 'args': ['<image_dir>/mingw64', r'.+\.la$']},
                    {'do': 'copyfile', 'args': ['<image_dir>/mingw64/bin/mingw32-make.exe', '<image_dir>/mingw64/bin/gmake.exe', 1]},
                ],
            },
            # STEP 2: Build ca.dll
            {
                'plugin': 'Perl::Dist::Strawberry::Step::BuildLibrary',
                'name': 'ca',
                'version': '__GLPI_AGENT_VERSION__',
                'folder': 'contrib/windows/packaging/tools/ca',
                'skip_if_file': 'tools/ca/ca.dll',
                'manifest': 'dll/ca.dll.manifest',
                'skip_configure': 1,
                'build_in_srcdir': 1,
                'make_use_cpus': 1,
                'skip_install': 1,
                'skip_test': 1,
            },
            # STEP 3: Sign ca.dll
            {
                'plugin': 'CustomCodeSigning',
                'files': [
                    'contrib/windows/packaging/tools/ca/ca.dll',
                ],
            },
        ]
    }


__all__ = ['build_steps']

