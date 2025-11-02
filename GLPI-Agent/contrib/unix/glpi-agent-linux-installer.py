#!/usr/bin/env python3
"""GLPI Agent Linux Installer - Main installer script"""

import os
import sys
import platform
import subprocess
from pathlib import Path

# Set environment locale
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'

# Add installer modules to path
sys.path.insert(0, str(Path(__file__).parent / 'installer'))

try:
    from InstallerVersion import get_version, DISTRO
    from Getopt import GetOptions, Help
    from LinuxDistro import LinuxDistro
    from Archive import Archive
except ImportError as e:
    print(f"Failed to import required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Check if running on Linux
if platform.system().lower() != 'linux':
    print(f"This installer can only be run on linux systems, not on {platform.system()}", file=sys.stderr)
    sys.exit(1)

# Parse options
options = GetOptions()
if not options:
    print(Help())
    sys.exit(1)

if options.get('help'):
    print(Help())
    sys.exit(0)

version = get_version()
if options.get('version'):
    print(f"GLPI-Agent installer for {DISTRO} v{version}")
    sys.exit(0)

# Handle list option
if options.get('list'):
    archive = Archive()
    archive.list()

# Extract action flags
uninstall = options.pop('uninstall', False)
install = options.pop('install', False)
clean = options.pop('clean', False)
reinstall = options.pop('reinstall', False)
extract = options.pop('extract', None)

# Default to install if no action specified
if not (install or uninstall or reinstall or extract):
    install = True

# Validate action combinations
if install and uninstall:
    print("--install and --uninstall options are mutually exclusive", file=sys.stderr)
    sys.exit(1)

if install and reinstall:
    print("--install and --reinstall options are mutually exclusive", file=sys.stderr)
    sys.exit(1)

if reinstall and uninstall:
    print("--reinstall and --uninstall options are mutually exclusive", file=sys.stderr)
    sys.exit(1)

# Check for root privileges if installing/uninstalling
if install or uninstall or reinstall:
    result = subprocess.run(['id', '-u'], capture_output=True, text=True)
    uid = result.stdout.strip()
    if not uid.isdigit() or int(uid) != 0:
        print("This installer can only be run as root when installing or uninstalling", file=sys.stderr)
        sys.exit(1)

# Create distribution handler
distro = LinuxDistro(options)
distro.analyze()
distro.init()

installed = distro.installed()
bypass = bool(extract and extract != "keep")

# Force installation for development version
if installed and not uninstall and not reinstall and not bypass:
    if version.endswith('-git') and version != installed:
        # Force installation for development version if still installed
        distro.verbose(f"Forcing installation of {version} over {installed}...")
        distro.allowDowngrade()

# Handle uninstall/reinstall
if not bypass and (uninstall or reinstall):
    distro.uninstall(clean)

# Handle clean
if not bypass and clean and (install or uninstall or reinstall):
    distro.clean()

# Handle install/reinstall
if not uninstall:
    archive = Archive()
    distro.extract(archive, extract)
    
    if install or reinstall:
        distro.info(f"Installing glpi-agent v{version}...")
        distro.install()

# Cleanup packages (called via END in Perl, but we'll do it explicitly)
try:
    distro.clean_packages()
except Exception:
    pass

sys.exit(0)

