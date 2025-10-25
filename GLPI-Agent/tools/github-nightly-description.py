#!/usr/bin/env python3
"""
GitHub Nightly Description Generator - Python Implementation

Generates nightly build description for GitHub releases.
Converted from the original Bash implementation.
"""

import sys
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path


def get_file_size(file_path: str) -> str:
    """
    Get human-readable file size.
    
    Args:
        file_path: Path to file
    
    Returns:
        Size string (e.g., "9M", "41M")
    """
    if not os.path.exists(file_path):
        return "~0M"
    
    size = os.path.getsize(file_path)
    
    # Convert to MB
    size_mb = size / (1024 * 1024)
    
    if size_mb < 1:
        return "~1M"
    else:
        return f"{int(size_mb)}M"


def generate_nightly_description(version: str, date: str = None, with_header: bool = False) -> str:
    """
    Generate nightly build description.
    
    Args:
        version: Version string
        date: Build date (defaults to current UTC time)
        with_header: Include header section
    
    Returns:
        Description string
    """
    if not date:
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Check if x86 MSI is available
    msi_x86_path = f"glpi-agent/GLPI-Agent-{version}-x86.msi"
    zip_x86_path = f"glpi-agent/GLPI-Agent-{version}-x86.zip"
    msi_x86 = ""
    
    if os.path.exists(msi_x86_path) and os.path.exists(zip_x86_path):
        msi_x86 = (f"32 bits | [GLPI-Agent-{version}-x86.msi](GLPI-Agent-{version}-x86.msi) | "
                  f"[GLPI-Agent-{version}-x86.zip](GLPI-Agent-{version}-x86.zip)")
    
    # Get Linux installer sizes
    lin_inst_path = f"glpi-agent-{version}-linux-installer.pl"
    lin_big_inst_path = f"glpi-agent-{version}-with-snap-linux-installer.pl"
    
    lin_inst_size = get_file_size(lin_inst_path) + "b"
    lin_big_inst_size = get_file_size(lin_big_inst_path) + "b"
    
    # Generate version anchors
    version_anchor = version.replace('.', '-')
    
    # Build description
    parts = []
    
    if with_header:
        parts.append("""---
layout: default
title: GLPI-Agent Nightly Builds
---
""")
    
    parts.append(f"""# GLPI-Agent v{version} nightly build

Built on {date}

## Windows <a href="#windows-{version_anchor}">#</a> {{#windows-{version_anchor}}}

Arch | Windows installer | Windows portable archive
---|:---|:---
64 bits | [GLPI-Agent-{version}-x64.msi](GLPI-Agent-{version}-x64.msi) | [GLPI-Agent-{version}-x64.zip](GLPI-Agent-{version}-x64.zip)
{msi_x86}

## MacOSX <a href="#macosx-{version_anchor}">#</a> {{#macosx-{version_anchor}}}

### MacOSX - Intel

Arch | Package
---|:---
x86_64 | PKG: [GLPI-Agent-{version}_x86_64.pkg](GLPI-Agent-{version}_x86_64.pkg)
x86_64 | DMG: [GLPI-Agent-{version}_x86_64.dmg](GLPI-Agent-{version}_x86_64.dmg)

### MacOSX - Apple Silicon

Arch | Package
---|:---
arm64 | PKG: [GLPI-Agent-{version}_arm64.pkg](GLPI-Agent-{version}_arm64.pkg)
arm64 | DMG: [GLPI-Agent-{version}_arm64.dmg](GLPI-Agent-{version}_arm64.dmg)

## Linux <a href="#linux-{version_anchor}">#</a> {{#linux-{version_anchor}}}

### Linux installer

Linux installer for redhat/centos/debian/ubuntu|Size
---|---
[glpi-agent-{version}-linux-installer.pl](glpi-agent-{version}-linux-installer.pl)|{lin_inst_size}

<p/>

Linux installer for redhat/centos/debian/ubuntu, including snap install support|Size
---|---
[glpi-agent-{version}-with-snap-linux-installer.pl](glpi-agent-{version}-with-snap-linux-installer.pl)|{lin_big_inst_size}

### Snap package for amd64

[glpi-agent_{version}_amd64.snap](glpi-agent_{version}_amd64.snap)

### AppImage Linux installer for x86-64

[glpi-agent-{version}-x86_64.AppImage](glpi-agent-{version}-x86_64.AppImage)

### Debian/Ubuntu packages

Better use [glpi-agent-{version}-linux-installer.pl](glpi-agent-{version}-linux-installer.pl) when possible.

Related agent task |Package
---|:---
Inventory| [glpi-agent_{version}_all.deb](glpi-agent_{version}_all.deb)
NetInventory | [glpi-agent-task-network_{version}_all.deb](glpi-agent-task-network_{version}_all.deb)
ESX | [glpi-agent-task-esx_{version}_all.deb](glpi-agent-task-esx_{version}_all.deb)
Collect | [glpi-agent-task-collect_{version}_all.deb](glpi-agent-task-collect_{version}_all.deb)
Deploy | [glpi-agent-task-deploy_{version}_all.deb](glpi-agent-task-deploy_{version}_all.deb)

### RPM packages

RPM packages are arch independents and installation may require some repository setups, better use [glpi-agent-{version}-linux-installer.pl](glpi-agent-{version}-linux-installer.pl) when possible.

Task |Packages
---|:---
Inventory| [glpi-agent-{version}.noarch.rpm](glpi-agent-{version}.noarch.rpm)
NetInventory | [glpi-agent-task-network-{version}.noarch.rpm](glpi-agent-task-network-{version}.noarch.rpm)
ESX | [glpi-agent-task-esx-{version}.noarch.rpm](glpi-agent-task-esx-{version}.noarch.rpm)
Collect | [glpi-agent-task-collect-{version}.noarch.rpm](glpi-agent-task-collect-{version}.noarch.rpm)
Deploy | [glpi-agent-task-deploy-{version}.noarch.rpm](glpi-agent-task-deploy-{version}.noarch.rpm)
WakeOnLan | [glpi-agent-task-wakeonlan-{version}.noarch.rpm](glpi-agent-task-wakeonlan-{version}.noarch.rpm)
Cron | [glpi-agent-cron-{version}.noarch.rpm](glpi-agent-cron-{version}.noarch.rpm)

## Sources <a href="#sources-{version_anchor}">#</a> {{#sources-{version_anchor}}}

[GLPI-Agent-{version}.tar.gz](GLPI-Agent-{version}.tar.gz)

## SHA256 sums
All sha256 sums for released filed can be retrieved from [glpi-agent-{version}.sha256](glpi-agent-{version}.sha256).

<p><a href='#content'>Back to top</a></p>
---
""")
    
    return ''.join(parts)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Generate nightly build description for GitHub releases'
    )
    parser.add_argument(
        '-v', '--version',
        required=True,
        help='Version string'
    )
    parser.add_argument(
        '--date',
        help='Build date (defaults to current UTC time)'
    )
    parser.add_argument(
        '--header',
        action='store_true',
        help='Include header section'
    )
    
    args = parser.parse_args()
    
    if not args.version:
        print("ERROR: VERSION not provided", file=sys.stderr)
        return 1
    
    description = generate_nightly_description(
        args.version,
        args.date,
        args.header
    )
    
    print(description, end='')
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

