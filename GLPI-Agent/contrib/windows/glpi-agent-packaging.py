#!/usr/bin/env python3
"""GLPI Agent Packaging Script - Main packaging script for Windows"""

import os
import sys
import re
import platform
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'packaging'))
sys.path.insert(0, 'lib')

try:
    from CustomCodeSigning import CustomCodeSigning
    from PerlBuildJob import build_job, PERL_BUILD_STEPS
    from GLPI.Agent.version import VERSION, PROVIDER
except ImportError as e:
    print(f"Failed to import required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Constants
PACKAGE_REVISION = "1"  # BEWARE: always start with 1
PROVIDED_BY = "Teclib Edition"

# HACK: make "use Perl::Dist::GLPI::Agent::Step::XXX" works as included plugin
# This would be handled by the build system

# Detect WiX installation
wixbin_dir = None
if platform.system() == 'Windows':
    try:
        import winreg
        
        for version in ['3.14', '3.11', '3.6', '3.5', '3.0']:
            try:
                # 0x200 = KEY_WOW64_32KEY
                key_path = f"SOFTWARE\\Microsoft\\Windows Installer XML\\{version}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ | 0x200) as key:
                    install_root = winreg.QueryValueEx(key, 'InstallRoot')[0]
                    
                    if os.path.isdir(install_root):
                        if os.path.isfile(os.path.join(install_root, 'candle.exe')) and \
                           os.path.isfile(os.path.join(install_root, 'light.exe')):
                            wixbin_dir = install_root
                            break
            except (OSError, FileNotFoundError):
                continue
    except ImportError:
        pass

if not wixbin_dir:
    print("Can't find WiX installation root in registry\n", file=sys.stderr)
    sys.exit(1)

provider = PROVIDER
version = VERSION

# Parse version tag
version_match = re.match(r'^[0-9.]+-(.*)$', version)
versiontag = version_match.group(1) if version_match else None

# Parse major, minor, revision
version_match = re.match(r'^(\d+)\.(\d+)\.?(\d+)?', version)
major = version_match.group(1) if version_match else "1"
minor = version_match.group(2) if version_match else "0"
revision = version_match.group(3) if version_match else "0"
if not revision:
    revision = "0"

# Handle GitHub environment variables
if os.environ.get('GITHUB_SHA'):
    github_sha = os.environ['GITHUB_SHA']
    github_ref_match = re.match(r'^([0-9a-f]{8})', github_sha)
    github_ref = github_ref_match.group(1) if github_ref_match else github_sha
    
    version = re.sub(r'-.*$', '', version)
    version = f"{version}-git{github_ref}"
    versiontag = f"git{github_ref}"

if os.environ.get('GITHUB_REF'):
    ref_match = re.match(r'refs/tags/(.+)$', os.environ['GITHUB_REF'])
    if ref_match:
        github_tag = ref_match.group(1)
        versiontag = ''
        
        if revision:
            version = github_tag
            tag_match = re.match(rf'^{major}\.{minor}\.{revision}-(.*)$', github_tag)
            if tag_match:
                versiontag = tag_match.group(1)
            elif github_tag != f"{major}.{minor}.{revision}":
                version = f"{major}.{minor}.{revision}-{github_tag}"
                versiontag = github_tag
        else:
            version = github_tag
            tag_match = re.match(rf'^{major}\.{minor}-(.*)$', github_tag)
            if tag_match:
                versiontag = tag_match.group(1)
            elif github_tag != f"{major}.{minor}":
                version = f"{major}.{minor}-{github_tag}"
                versiontag = github_tag


def build_app(arch: str, notest: bool, sign: bool):
    """
    Build application for given architecture.
    
    Args:
        arch: Architecture ('x86' or 'x64')
        notest: Skip tests flag
        sign: Code signing flag
        
    Returns:
        Build application object
    """
    package_rev = os.environ.get('PACKAGE_REVISION', PACKAGE_REVISION)
    
    # This would instantiate the Perl::Dist::GLPI::Agent class
    # In Python, this would be adapted to a Python build framework
    app_config = {
        '_perl_version': '5.42.0',  # PERL_VERSION
        '_revision': package_rev,
        '_provider': provider,
        '_provided_by': PROVIDED_BY,
        '_no_test': notest,
        'agent_version': version,
        'agent_fullver': f"{major}.{minor}.{revision}.{package_rev}",
        'agent_vernum': f"{major}.{minor}.{revision}" if revision else f"{major}.{minor}",
        'agent_vertag': versiontag or '',
        'agent_fullname': f'{provider} Agent',
        'agent_rootdir': f'{provider}-Agent',
        'agent_localguid': None,  # Would use Data::UUID equivalent
        'agent_regpath': f"Software\\{provider}-Agent",
        'service_name': f"{provider.lower()}-agent",
        'msi_sharedir': 'contrib/windows/packaging',
        'arch': arch,
        '_dllsuffix': '_' if arch == "x86" else '__',
        '_restore_step': PERL_BUILD_STEPS,
        'codesigning': sign,
        'image_dir': f"C:\\Strawberry-perl-for-{provider}-Agent",
        'working_dir': f"C:\\Strawberry-perl-for-{provider}-Agent_build",
        'wixbin_dir': wixbin_dir,
        'notest_modules': True,
        'nointeractive': True,
        'restorepoints': True,
    }
    
    # In a real implementation, this would create the build app object
    # For now, return the config
    return app_config


# Parse command line arguments
do_archs = {}
notest = False
sign = False

args = sys.argv[1:]
i = 0
while i < len(args):
    arg = args[i]
    if arg == "--arch":
        i += 1
        if i < len(args):
            arch = args[i]
            if re.match(r'^x(86|64)$', arch):
                do_archs[arch] = 32 if arch == "x86" else 64
    elif arg == "--all":
        do_archs = {'x86': 32, 'x64': 64}
    elif arg == "--no-test":
        notest = True
    elif arg.startswith("--code-signing="):
        value = arg.split('=', 1)[1]
        sign = bool(re.match(r'^yes|1$', value, re.IGNORECASE))
    else:
        print(f"Unsupported option: {arg}\n", file=sys.stderr)
    i += 1

# Still select a default arch if none has been selected
if not do_archs:
    do_archs['x64'] = 64

if 'x86' in do_archs:
    print("32 bits packaging build no more supported\n", file=sys.stderr)
    sys.exit(1)

for arch in sorted(do_archs.keys()):
    print(f"Building {arch} packages...\n")
    app = build_app(arch, notest, sign)
    # app.do_job() would be called here
    # global_dump_FINAL.txt must exist in debug_dir if all steps have been passed
    debug_dir = app.get('debug_dir', '')
    final_file = os.path.join(debug_dir, 'global_dump_FINAL.txt') if debug_dir else ''
    if not os.path.exists(final_file):
        sys.exit(1)

print("All packages building processing passed\n")
sys.exit(0)

