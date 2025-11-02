#!/usr/bin/env python3
"""DebDistro - Debian/Ubuntu distribution handler"""

import os
import re
import subprocess
from typing import Dict, List, Optional
from .LinuxDistro import LinuxDistro
from .InstallerVersion import get_version

DEBREVISION = "1"
DEBVERSION = get_version()
# Add package revision on official releases
if '-' not in DEBVERSION:
    DEBVERSION = f"{DEBVERSION}-{DEBREVISION}"

DebPackages = {
    "glpi-agent": re.compile(r'^inventory$', re.IGNORECASE),
    "glpi-agent-task-network": re.compile(r'^netdiscovery|netinventory|network$', re.IGNORECASE),
    "glpi-agent-task-collect": re.compile(r'^collect$', re.IGNORECASE),
    "glpi-agent-task-esx": re.compile(r'^esx$', re.IGNORECASE),
    "glpi-agent-task-deploy": re.compile(r'^deploy$', re.IGNORECASE),
}

DebInstallTypes = {
    'all': [
        'glpi-agent',
        'glpi-agent-task-network',
        'glpi-agent-task-collect',
        'glpi-agent-task-esx',
        'glpi-agent-task-deploy',
    ],
    'typical': ['glpi-agent'],
    'network': [
        'glpi-agent',
        'glpi-agent-task-network',
    ],
}


class DebDistro(LinuxDistro):
    """Debian/Ubuntu distribution handler"""
    
    def init(self):
        """Initialize Debian distribution"""
        # Store installation status for each supported package
        for deb in DebPackages.keys():
            result = subprocess.run(
                ['dpkg-query', '--show', '--showformat', '${Version}', deb],
                capture_output=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                # Remove epoch if present
                version = re.sub(r'^\d+:', '', version)
                self._packages[deb] = version
        
        # Try to figure out installation type from installed packages
        if self._packages and not self._type:
            installed = ','.join(sorted(self._packages.keys()))
            self._type = "custom"
            for inst_type, pkgs in DebInstallTypes.items():
                install_type = ','.join(sorted(pkgs))
                if installed == install_type:
                    self._type = inst_type
                    break
            self.verbose(f"Guessed installation type: {self._type}")
        
        # Call parent init
        super().init()
    
    def _extract_deb(self, deb: str) -> str:
        """Extract DEB package from archive"""
        pkg = f"{deb}_{DEBVERSION}_all.deb"
        self.verbose(f"Extracting {pkg} ...")
        if not self._archive.extract(f"pkg/deb/{pkg}"):
            raise IOError(f"Failed to extract {pkg}")
        
        pwd = os.environ.get('PWD', subprocess.run(['pwd'], capture_output=True, text=True).stdout.strip())
        pkg_path = f"{pwd}/{pkg}"
        # Quote if path contains spaces
        if ' ' in pwd:
            pkg_path = f"'{pkg_path}'"
        return pkg_path
    
    def install(self):
        """Install Debian packages"""
        self.verbose(f"Trying to install glpi-agent v{DEBVERSION} on {self._release} release ({self._name}:{self._version})...")
        
        inst_type = self._type or "typical"
        pkgs = {'glpi-agent': 1}
        
        if inst_type in DebInstallTypes:
            for pkg in DebInstallTypes[inst_type]:
                pkgs[pkg] = 1
        else:
            # Custom type - parse task list
            for task in inst_type.split(','):
                for pkg, pattern in DebPackages.items():
                    if pattern.match(task):
                        pkgs[pkg] = 1
                        break
        
        # Check installed packages
        if self._packages:
            # Auto-select still installed packages
            for pkg in self._packages.keys():
                pkgs[pkg] = 1
            
            for pkg in list(pkgs.keys()):
                if pkg in self._packages:
                    if self._packages[pkg] == DEBVERSION:
                        self.verbose(f"{pkg} still installed and up-to-date")
                        del pkgs[pkg]
                    else:
                        self.verbose(f"{pkg} will be upgraded")
        
        # Don't install skipped packages
        for skip_pkg in list(pkgs.keys()):
            if skip_pkg in self._skip:
                del pkgs[skip_pkg]
        
        pkg_list = sorted(pkgs.keys())
        if pkg_list:
            # Get dependencies
            deps = self.getDeps("deb")
            for dep in deps:
                pkgs[dep] = dep
            
            # Extract packages
            for pkg in pkg_list:
                pkgs[pkg] = self._extract_deb(pkg)
            
            # Check for dmidecode
            if 'dmidecode' not in self._skip:
                result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
                arch = result.stdout.strip()
                if re.match(r'^(i.86|x86_64)$', arch) and not self.which("dmidecode"):
                    self.verbose("Trying to also install dmidecode ...")
                    pkgs['dmidecode'] = "dmidecode"
            
            # Check for pci.ids
            if not os.path.exists("/usr/share/misc/pci.ids"):
                result = subprocess.run(
                    ['dpkg-query', '--show', '--showformat', '${Package}', 'pciutils'],
                    capture_output=True,
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    self.verbose("Trying to also install pci.ids ...")
                    pkgs["pci.ids"] = "pci.ids"
            
            # Check for usb.ids
            if not os.path.exists("/usr/share/misc/usb.ids"):
                result = subprocess.run(
                    ['dpkg-query', '--show', '--showformat', '${Package}', 'usbutils'],
                    capture_output=True,
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    self.verbose("Trying to also install usb.ids ...")
                    pkgs["usb.ids"] = "usb.ids"
            
            debs = sorted(pkgs.values())
            options = ["-y"]
            if self.downgradeAllowed():
                options.append("--allow-downgrades")
            
            cmd = f"apt {' '.join(options)} install {' '.join(debs)} 2>/dev/null"
            err = self.run(cmd)
            if err:
                raise RuntimeError("Failed to install glpi-agent")
            self._installed = debs
        else:
            self._installed = 1
        
        # Call parent installer
        super().install()
    
    def uninstall(self):
        """Uninstall Debian packages"""
        debs = sorted(self._packages.keys())
        
        if not debs:
            self.info("glpi-agent is not installed")
            return
        
        self.uninstall_service()
        
        if len(debs) == 1:
            self.info("Uninstalling glpi-agent package...")
        else:
            self.info(f"Uninstalling {len(debs)} glpi-agent related packages...")
        
        err = self.run(f"apt -y purge --autoremove {' '.join(debs)} 2>/dev/null")
        if err:
            raise RuntimeError("Failed to uninstall glpi-agent")
        
        for deb in debs:
            del self._packages[deb]
        
        # Remove cron file if found
        if os.path.exists("/etc/cron.hourly/glpi-agent"):
            os.unlink("/etc/cron.hourly/glpi-agent")
    
    def clean(self):
        """Clean Debian-specific files"""
        super().clean()
        
        if os.path.exists("/etc/default/glpi-agent"):
            os.unlink("/etc/default/glpi-agent")
    
    def install_cron(self):
        """Install cron job for Debian"""
        self.info("glpi-agent will be run every hour via cron")
        self.verbose("Disabling glpi-agent service...")
        ret = self.run("systemctl disable glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to disable glpi-agent service")
            return
        
        self.verbose("Stopping glpi-agent service if running...")
        ret = self.run("systemctl stop glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to stop glpi-agent service")
            return
        
        self.verbose("Installing glpi-agent hourly cron file...")
        cron = self.open_os_file('/etc/cron.hourly/glpi-agent', '>')
        cron.write('''#!/bin/bash

NAME=glpi-agent
LOG=/var/log/$NAME-cron.log

exec >>$LOG 2>&1

[ -f /etc/default/$NAME ] || exit 0
source /etc/default/$NAME
export PATH

: ${OPTIONS:=--wait 120 --lazy}

echo "[$(date '+%c')] Running $NAME $OPTIONS"
/usr/bin/$NAME $OPTIONS
echo "[$(date '+%c')] End of cron job ($PATH)"
''')
        self.close_os_file()
        self.chmod_os_file(0o755, '/etc/cron.hourly/glpi-agent')
        
        if not self.os_file_exists('/etc/default/glpi-agent'):
            self.verbose("Installing glpi-agent system default config...")
            default = self.open_os_file('/etc/default/glpi-agent', '>')
            default.write('''# By default, ask agent to wait a random time
OPTIONS="--wait 120"

# By default, runs are lazy, so the agent won't contact the server before it's time to
OPTIONS="$OPTIONS --lazy"
''')
            self.close_os_file()

