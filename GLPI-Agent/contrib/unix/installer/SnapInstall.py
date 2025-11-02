#!/usr/bin/env python3
"""SnapInstall - Snap package installation handler"""

import os
import re
import subprocess
from typing import Optional
from .LinuxDistro import LinuxDistro
from .InstallerVersion import get_version


class SnapInstall(LinuxDistro):
    """Snap package installation handler"""
    
    def init(self):
        """Initialize Snap installation"""
        if not self.which("snap"):
            raise ValueError("Can't install glpi-agent via snap without snap installed")
        
        self._bin = "/snap/bin/glpi-agent"
        self._snap = {}
        
        # Store installation status of the current snap
        result = subprocess.run(
            ['snap', 'info', 'glpi-agent'],
            capture_output=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            match = re.search(r'^installed:\s+(\S+)', result.stdout, re.MULTILINE)
            if match:
                self._snap['version'] = match.group(1)
    
    def install(self):
        """Install snap package"""
        version = get_version()
        self.verbose(f"Trying to install glpi-agent v{version} via snap on {self._release} release ({self._name}:{self._version})...")
        
        # Check installed packages
        if self._snap:
            snap_version = self._snap.get('version', '')
            if snap_version and re.match(f'^{re.escape(version)}', snap_version):
                self.verbose("glpi-agent still installed and up-to-date")
            else:
                self.verbose("glpi-agent will be upgraded")
                self._snap = {}
        
        if not self._snap:
            # Find snap file in archive
            snap_files = [f for f in self._archive.files() if re.match(r'^pkg/snap/.*\.snap$', f)]
            if not snap_files:
                raise ValueError("No snap included in archive")
            
            snap = snap_files[0]
            snap_name = re.sub(r'^pkg/snap/', '', snap)
            self.verbose(f"Extracting {snap_name} ...")
            
            if not self._archive.extract(snap):
                raise IOError(f"Failed to extract {snap}")
            
            err = self.run(f"snap install --classic --dangerous {snap_name}")
            if err:
                raise RuntimeError("Failed to install glpi-agent snap package")
            self._installed = [snap_name]
        else:
            self._installed = 1
        
        # Call parent installer
        super().install()
    
    def configure(self, folder: Optional[str] = None):
        """Configure agent using snap folder"""
        # Call parent configure using snap folder
        super().configure("/var/snap/glpi-agent/current")
    
    def uninstall(self, purge: bool = False):
        """Uninstall snap package"""
        if not self._snap:
            self.info("glpi-agent is not installed via snap")
            return
        
        self.info("Uninstalling glpi-agent snap...")
        command = "snap remove glpi-agent"
        if purge:
            command += " --purge"
        
        err = self.run(command)
        if err:
            raise RuntimeError("Failed to uninstall glpi-agent snap")
        
        # Remove cron file if found
        if os.path.exists("/etc/cron.hourly/glpi-agent"):
            os.unlink("/etc/cron.hourly/glpi-agent")
        
        self._snap = {}
    
    def clean(self):
        """Clean snap-specific files"""
        if self._snap:
            raise ValueError("Can't clean glpi-agent related files if it is currently installed")
        
        self.info("Cleaning...")
        # clean uninstall is mostly done using --purge option in uninstall
        if os.path.exists("/etc/default/glpi-agent"):
            os.unlink("/etc/default/glpi-agent")
    
    def install_service(self):
        """Install snap service"""
        self.info("Enabling glpi-agent service...")
        
        ret = self.run("snap start --enable glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to enable glpi-agent service")
            return
        
        if self._runnow:
            # Still handle run now here to avoid calling systemctl in parent
            self._runnow = False
            ret = self.run(self._bin + " --set-forcerun" + ("" if self._verbose else " 2>/dev/null"))
            if ret:
                self.info("Failed to ask glpi-agent service to run now")
                return
            
            ret = self.run("snap restart glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
            if ret:
                self.info("Failed to restart glpi-agent service on run now")
    
    def install_cron(self):
        """Install cron job for snap"""
        self.info("glpi-agent will be run every hour via cron")
        self.verbose("Disabling glpi-agent service...")
        ret = self.run("snap stop --disable glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to disable glpi-agent service")
            return
        
        self.verbose("Installing glpi-agent hourly cron file...")
        cron = self.open_os_file('/etc/cron.hourly/glpi-agent', '>')
        cron.write('''#!/bin/bash

NAME=glpi-agent-cron
LOG=/var/log/$NAME.log

exec >>$LOG 2>&1

[ -f /etc/default/$NAME ] || exit 0
source /etc/default/$NAME
export PATH

: ${OPTIONS:=--wait 120 --lazy}

echo "[$(date '+%c')] Running $NAME $OPTIONS"
/snap/bin/$NAME $OPTIONS
echo "[$(date '+%c')] End of cron job ($PATH)"
''')
        self.close_os_file()
        
        if not self.os_file_exists('/etc/default/glpi-agent'):
            self.verbose("Installing glpi-agent system default config...")
            default = self.open_os_file('/etc/default/glpi-agent', '>')
            default.write('''# By default, ask agent to wait a random time
OPTIONS="--wait 120"

# By default, runs are lazy, so the agent won't contact the server before it's time to
OPTIONS="$OPTIONS --lazy"
''')
            self.close_os_file()

