#!/usr/bin/env python3
"""ToolchainBuildJob - Toolchain build job configuration"""

from typing import Dict, Any
import time

# Toolchain setup constants
TOOLCHAIN_BASE_URL = 'https://github.com/brechtsanders/winlibs_mingw/releases/download'
TOOLCHAIN_VERSION = '15.2.0posix-13.0.0-msvcrt-r1'
TOOLCHAIN_ARCHIVE = 'winlibs-x86_64-posix-seh-gcc-15.2.0-mingw-w64msvcrt-13.0.0-r1.zip'


def toolchain_build_steps(arch: str) -> Dict[str, Any]:
    """
    Get toolchain build steps configuration.
    
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
        'app_simplename': "extlibs",
        'app_version': version,
        'bits': bits,
        'build_job_steps': [
            # STEP 0: Toolchain download & install
            {
                'plugin': 'Perl::Dist::Strawberry::Step::ToolChain',
                'install_packages': {
                    'gcc-toolchain': {
                        'url': f"{TOOLCHAIN_BASE_URL}/{TOOLCHAIN_VERSION}/{TOOLCHAIN_ARCHIVE}",
                    }
                }
            },
            # STEP 1: Toolchain update
            {
                'plugin': 'Perl::Dist::Strawberry::Step::ToolChainUpdate',
                'commands': [
                    {'do': 'copyfile', 'args': ['<build_dir>/mingw64/bin/mingw32-make.exe', '<build_dir>/mingw64/bin/make.exe', 1]},
                    {'do': 'copyfile', 'args': ['<build_dir>/mingw64/bin/mingw32-make.exe', '<build_dir>/mingw64/bin/gmake.exe', 1]},
                ],
            },
            # STEP 2: Msys2-base download
            {
                'plugin': 'Perl::Dist::Strawberry::Step::Msys2',
                'name': 'msys2-base',
                'version': '20250830',
                'folder': '2025-08-30',
                'url': 'https://github.com/msys2/msys2-installer/releases/download/<folder>/<name>-x86_64-<version>.tar.xz',
                'dest': 'msys64',
            },
            # STEP 3: Msys2-base update
            {
                'plugin': 'Perl::Dist::Strawberry::Step::Msys2Package',
                'name': 'msys2-utils',
                'install': ['patch', 'diffutils'],
                'skip_if_file': 'usr/bin/patch.exe',
                'dest': 'msys64',
            },
            # STEP 4: Toolchain check
            {
                'plugin': 'Perl::Dist::Strawberry::Step::Control',
                'commands': [
                    {'title': 'GCC', 'run': 'gcc', 'args': ['--version']},
                    {'title': 'AR', 'run': 'ar', 'args': ['--version']},
                    {'title': 'MAKE', 'run': 'make', 'args': ['-v']},
                    {'title': 'BASH', 'run': 'bash', 'args': ['--version']},
                    {'title': 'PATCH', 'run': 'patch', 'args': ['--version']},
                    {'title': 'UNAME', 'run': 'uname', 'args': ['--version']},
                ],
            },
            # Additional steps would follow here...
            # For brevity, including the structure but note that the full
            # configuration includes many more steps for building libraries
        ]
    }


__all__ = ['toolchain_build_steps', 'TOOLCHAIN_BASE_URL', 'TOOLCHAIN_VERSION', 'TOOLCHAIN_ARCHIVE']

