#!/usr/bin/env python3
"""
GitHub Release Description Generator - Python Implementation

Generates release description for GitHub releases.
Converted from the original Bash implementation.
"""

import sys
import os
import argparse
from pathlib import Path


def generate_release_description(version: str, tag: str = None, 
                                 repo: str = None) -> str:
    """
    Generate release description.
    
    Args:
        version: Version string
        tag: Git tag (defaults to version)
        repo: Repository URL
    
    Returns:
        Description string
    """
    if not tag:
        tag = version
    
    if not repo:
        repo = os.environ.get('REPO', 'https://github.com/glpi-project/glpi-agent')
    
    # Determine Debian and RPM revision suffixes
    debrev = ""
    rpmrev = ""
    
    # If tag doesn't contain a dash, add revision suffixes
    if '-' not in tag:
        debrev = "-1"
        rpmrev = "-1"
    
    description = f"""Here you can download GLPI-Agent v{version} packages.

Don't forget to follow our [installation documentation](https://glpi-agent.readthedocs.io/en/latest/installation/).

## Windows
Arch | Windows installer | Windows portable archive
---|:---|:---
64 bits | [GLPI-Agent-{version}-x64.msi]({repo}/releases/download/{tag}/GLPI-Agent-{version}-x64.msi) | [GLPI-Agent-{version}-x64.zip]({repo}/releases/download/{tag}/GLPI-Agent-{version}-x64.zip)

## MacOSX

### MacOSX - Intel
Arch | Package
---|:---
x86_64 | PKG: [GLPI-Agent-{version}_x86_64.pkg]({repo}/releases/download/{tag}/GLPI-Agent-{version}_x86_64.pkg)
x86_64 | DMG: [GLPI-Agent-{version}_x86_64.dmg]({repo}/releases/download/{tag}/GLPI-Agent-{version}_x86_64.dmg)

### MacOSX - Apple Silicon
Arch | Package
---|:---
arm64 | PKG: [GLPI-Agent-{version}_arm64.pkg]({repo}/releases/download/{tag}/GLPI-Agent-{version}_arm64.pkg)
arm64 | DMG: [GLPI-Agent-{version}_arm64.dmg]({repo}/releases/download/{tag}/GLPI-Agent-{version}_arm64.dmg)

## Linux

### Linux installer
Linux installer for redhat/centos/debian/ubuntu|Size
---|---
[glpi-agent-{version}-linux-installer.pl]({repo}/releases/download/{tag}/glpi-agent-{version}-linux-installer.pl)|~9Mb

Linux installer for redhat/centos/debian/ubuntu with also snap install support|Size
---|---
[glpi-agent-{version}-with-snap-linux-installer.pl]({repo}/releases/download/{tag}/glpi-agent-{version}-with-snap-linux-installer.pl)|~41Mb

### Snap package for amd64
[glpi-agent_{version}_amd64.snap]({repo}/releases/download/{tag}/glpi-agent_{version}_amd64.snap)

### AppImage Linux installer for x86-64
[glpi-agent-{version}-x86_64.AppImage]({repo}/releases/download/{tag}/glpi-agent-{version}-x86_64.AppImage)

### Debian/Ubuntu packages
Better use [glpi-agent-{version}-linux-installer.pl]({repo}/releases/download/{tag}/glpi-agent-{version}-linux-installer.pl) when possible.
Related agent task |Package
---|:---
Inventory| [glpi-agent_{version}{debrev}_all.deb]({repo}/releases/download/{tag}/glpi-agent_{version}{debrev}_all.deb)
NetInventory | [glpi-agent-task-network_{version}{debrev}_all.deb]({repo}/releases/download/{tag}/glpi-agent-task-network_{version}{debrev}_all.deb)
ESX | [glpi-agent-task-esx_{version}{debrev}_all.deb]({repo}/releases/download/{tag}/glpi-agent-task-esx_{version}{debrev}_all.deb)
Collect | [glpi-agent-task-collect_{version}{debrev}_all.deb]({repo}/releases/download/{tag}/glpi-agent-task-collect_{version}{debrev}_all.deb)
Deploy | [glpi-agent-task-deploy_{version}{debrev}_all.deb]({repo}/releases/download/{tag}/glpi-agent-task-deploy_{version}{debrev}_all.deb)

### RPM packages
RPM packages are arch independents and installation may require some repository setups, better use [glpi-agent-{version}-linux-installer.pl]({repo}/releases/download/{tag}/glpi-agent-{version}-linux-installer.pl) when possible.
Task |Packages
---|:---
Inventory| [glpi-agent-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-{version}{rpmrev}.noarch.rpm)
NetInventory | [glpi-agent-task-network-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-task-network-{version}{rpmrev}.noarch.rpm)
ESX | [glpi-agent-task-esx-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-task-esx-{version}{rpmrev}.noarch.rpm)
Collect | [glpi-agent-task-collect-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-task-collect-{version}{rpmrev}.noarch.rpm)
Deploy | [glpi-agent-task-deploy-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-task-deploy-{version}{rpmrev}.noarch.rpm)
WakeOnLan | [glpi-agent-task-wakeonlan-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-task-wakeonlan-{version}{rpmrev}.noarch.rpm)
Cron | [glpi-agent-cron-{version}{rpmrev}.noarch.rpm]({repo}/releases/download/{tag}/glpi-agent-cron-{version}{rpmrev}.noarch.rpm)

## Sources
[GLPI-Agent-{version}.tar.gz]({repo}/releases/download/{tag}/GLPI-Agent-{version}.tar.gz)

## SHA256 sums
All sha256 sums for released filed can be retrieved from [glpi-agent-{version}.sha256]({repo}/releases/download/{tag}/glpi-agent-{version}.sha256).
"""
    
    return description


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Generate release description for GitHub releases'
    )
    parser.add_argument(
        '-v', '--version',
        help='Version string (defaults to GITHUB_REF tag)'
    )
    parser.add_argument(
        '-t', '--tag',
        help='Git tag (defaults to version or GITHUB_REF)'
    )
    parser.add_argument(
        '--repo',
        help='Repository URL',
        default='https://github.com/glpi-project/glpi-agent'
    )
    
    args = parser.parse_args()
    
    # Get tag from GITHUB_REF if available
    github_ref = os.environ.get('GITHUB_REF', '')
    if github_ref.startswith('refs/tags/'):
        ref_tag = github_ref[len('refs/tags/'):]
    else:
        ref_tag = None
    
    # Determine tag and version
    tag = args.tag or ref_tag
    version = args.version or tag
    
    if not tag or tag == github_ref:
        print("ERROR: GITHUB_REF is not referencing a tag", file=sys.stderr)
        return 1
    
    if not version:
        print("ERROR: No version provided", file=sys.stderr)
        return 1
    
    # Generate and write description to file
    description = generate_release_description(version, tag, args.repo)
    
    with open('release-description.md', 'w', encoding='utf-8', newline='\n') as f:
        f.write(description)
    
    print(f"Release description written to release-description.md")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

