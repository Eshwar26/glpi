#!/usr/bin/env python3
"""RpmDistro - RPM-based distribution handler"""

import os
import re
import subprocess
from typing import Dict, List, Optional
from .LinuxDistro import LinuxDistro
from .InstallerVersion import get_version

RPMREVISION = "1"
RPMVERSION = get_version()
# Add package revision on official releases
if '-' not in RPMVERSION:
    RPMVERSION = f"{RPMVERSION}-{RPMREVISION}"

RpmPackages = {
    "glpi-agent": re.compile(r'^inventory$', re.IGNORECASE),
    "glpi-agent-task-network": re.compile(r'^netdiscovery|netinventory|network$', re.IGNORECASE),
    "glpi-agent-task-collect": re.compile(r'^collect$', re.IGNORECASE),
    "glpi-agent-task-esx": re.compile(r'^esx$', re.IGNORECASE),
    "glpi-agent-task-deploy": re.compile(r'^deploy$', re.IGNORECASE),
    "glpi-agent-task-wakeonlan": re.compile(r'^wakeonlan|wol$', re.IGNORECASE),
    "glpi-agent-cron": None,  # Special package, not matched by task
}

RpmInstallTypes = {
    'all': [
        'glpi-agent',
        'glpi-agent-task-network',
        'glpi-agent-task-collect',
        'glpi-agent-task-esx',
        'glpi-agent-task-deploy',
        'glpi-agent-task-wakeonlan',
    ],
    'typical': ['glpi-agent'],
    'network': [
        'glpi-agent',
        'glpi-agent-task-network',
    ],
}


class RpmDistro(LinuxDistro):
    """RPM-based distribution handler"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._yum = None
        self._zypper = None
        self._dnf = None
    
    def init(self):
        """Initialize RPM distribution"""
        # Store installation status for each supported package
        for rpm in RpmPackages.keys():
            result = subprocess.run(
                ['rpm', '-q', '--queryformat', '%{VERSION}-%{RELEASE}', rpm],
                capture_output=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self._packages[rpm] = version
        
        # Try to figure out installation type from installed packages
        if self._packages and not self._type:
            installed = ','.join(sorted(self._packages.keys()))
            self._type = "custom"
            for inst_type, pkgs in RpmInstallTypes.items():
                install_type = ','.join(sorted(pkgs))
                if installed == install_type:
                    self._type = inst_type
                    break
            self.verbose(f"Guessed installation type: {self._type}")
        
        # Call parent init
        super().init()
    
    def _extract_rpm(self, rpm: str) -> str:
        """Extract RPM package from archive"""
        pkg = f"{rpm}-{RPMVERSION}.noarch.rpm"
        self.verbose(f"Extracting {pkg} ...")
        if not self._archive.extract(f"pkg/rpm/{pkg}"):
            raise IOError(f"Failed to extract {pkg}")
        return pkg
    
    def _prepareDistro(self):
        """Prepare distribution-specific repositories and settings"""
        self._dnf = True
        
        # Still ready for Fedora
        if re.search(r'fedora', self._name, re.IGNORECASE):
            return
        
        # Get major version number
        version_match = re.match(r'^(\d+)', str(self._version))
        v = int(version_match.group(1)) if version_match else 0
        if not v:
            return
        
        # Enable repo for RedHat or CentOS
        if re.search(r'red\s?hat', self._name, re.IGNORECASE):
            # Since RHEL 8, enable codeready-builder repo
            if v < 8:
                self._yum = True
                self._dnf = None
            else:
                result = subprocess.run(['arch'], capture_output=True, text=True)
                arch = result.stdout.strip()
                self.verbose(f"Checking codeready-builder-for-rhel-{v}-{arch}-rpms repository repository is enabled")
                ret = self.run(f"subscription-manager repos --enable codeready-builder-for-rhel-{v}-{arch}-rpms")
                if ret:
                    raise RuntimeError(f"Can't enable codeready-builder-for-rhel-{v}-{arch}-rpms repository")
        
        elif re.search(r'oracle linux', self._name, re.IGNORECASE):
            # On Oracle Linux server 8+, we need "olX_codeready_builder"
            if v < 8:
                self._yum = True
                self._dnf = None
            else:
                self.verbose("Checking Oracle Linux CodeReady Builder repository is enabled")
                ret = self.run(f"dnf config-manager --set-enabled ol{v}_codeready_builder")
                if ret:
                    raise RuntimeError("Can't enable CodeReady Builder repository")
        
        elif re.search(r'rocky|almalinux', self._name, re.IGNORECASE):
            # On Rocky 8, we need PowerTools
            # On Rocky/AlmaLinux 9+, we need CRB
            if v >= 9:
                self.verbose("Checking CRB repository is enabled")
                ret = self.run("dnf config-manager --set-enabled crb")
                if ret:
                    raise RuntimeError("Can't enable CRB repository")
            else:
                self.verbose("Checking PowerTools repository is enabled")
                ret = self.run("dnf config-manager --set-enabled powertools")
                if ret:
                    raise RuntimeError("Can't enable PowerTools repository")
        
        elif re.search(r'centos', self._name, re.IGNORECASE):
            # On CentOS 8, we need PowerTools
            # Since CentOS 9, we need CRB
            if v >= 9:
                self.verbose("Checking CRB repository is enabled")
                ret = self.run("dnf config-manager --set-enabled crb")
                if ret:
                    raise RuntimeError("Can't enable CRB repository")
            elif v == 8:
                self.verbose("Checking PowerTools repository is enabled")
                ret = self.run("dnf config-manager --set-enabled powertools")
                if ret:
                    raise RuntimeError("Can't enable PowerTools repository")
            else:
                self._yum = True
                self._dnf = None
        
        elif re.search(r'opensuse', self._name, re.IGNORECASE):
            self._zypper = True
            self._dnf = None
            self.verbose("Checking devel_languages_perl repository is enabled")
            # Always quiet this test even on verbose mode
            ret = self.run("zypper -n repos devel_languages_perl" + ("" if self._verbose else " >/dev/null"))
            if ret:
                self.verbose("Installing devel_languages_perl repository...")
                release = self._release.replace(' ', '_')
                ret = 0
                for version in [self._version, release]:
                    ret = self.run(f"zypper -n --gpg-auto-import-keys addrepo https://download.opensuse.org/repositories/devel:/languages:/perl/{version}/devel:languages:perl.repo")
                    if not ret:
                        break
                if ret:
                    raise RuntimeError("Can't install devel_languages_perl repository")
            self.verbose("Enable devel_languages_perl repository...")
            ret = self.run("zypper -n modifyrepo -e devel_languages_perl")
            if ret:
                raise RuntimeError("Can't enable required devel_languages_perl repository")
            self.verbose("Refresh devel_languages_perl repository...")
            ret = self.run("zypper -n --gpg-auto-import-keys refresh devel_languages_perl")
            if ret:
                raise RuntimeError("Can't refresh devel_languages_perl repository")
        
        # We need EPEL only on redhat/centos
        if not self._zypper:
            result = subprocess.run(
                ['rpm', '-q', '--queryformat', '%{VERSION}', 'epel-release'],
                capture_output=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            epel = result.stdout.strip()
            if result.returncode == 0 and epel == str(v):
                self.verbose(f"EPEL {v} repository still installed")
            else:
                self.info(f"Installing EPEL {v} repository...")
                cmd = "yum" if self._yum else "dnf"
                if self.system(f"{cmd} -y install epel-release") != 0:
                    epelcmd = f"{cmd} -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-{v}.noarch.rpm"
                    ret = self.run(epelcmd)
                    if ret:
                        raise RuntimeError(f"Can't install EPEL {v} repository")
    
    def install(self):
        """Install RPM packages"""
        self.verbose(f"Trying to install glpi-agent v{RPMVERSION} on {self._release} release ({self._name}:{self._version})...")
        
        inst_type = self._type or "typical"
        pkgs = {'glpi-agent': 1}
        
        if inst_type in RpmInstallTypes:
            for pkg in RpmInstallTypes[inst_type]:
                pkgs[pkg] = 1
        else:
            # Custom type - parse task list
            for task in inst_type.split(','):
                for pkg, pattern in RpmPackages.items():
                    if pattern and pattern.match(task):
                        pkgs[pkg] = 1
                        break
        
        # Add cron package if cron mode
        if self._cron:
            pkgs["glpi-agent-cron"] = 1
        
        # Check installed packages
        if self._packages:
            # Auto-select still installed packages
            for pkg in self._packages.keys():
                pkgs[pkg] = 1
            
            for pkg in list(pkgs.keys()):
                if pkg in self._packages:
                    if self._packages[pkg] == RPMVERSION:
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
            deps = self.getDeps("rpm")
            for dep in deps:
                pkgs[dep] = dep
            
            # Extract packages
            for pkg in pkg_list:
                pkgs[pkg] = self._extract_rpm(pkg)
            
            # Check for dmidecode
            if 'dmidecode' not in self._skip:
                result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
                arch = result.stdout.strip()
                if re.match(r'^(i.86|x86_64)$', arch) and not self.which("dmidecode"):
                    self.verbose("Trying to also install dmidecode ...")
                    pkgs['dmidecode'] = "dmidecode"
            
            rpms = sorted(pkgs.values())
            self._prepareDistro()
            
            if self._yum:
                command = f"yum -y install {' '.join(rpms)}"
            elif self._zypper:
                command = f"zypper -n install -y --allow-unsigned-rpm {' '.join(rpms)}"
            elif self._dnf:
                command = f"dnf -y install --setopt=localpkg_gpgcheck=0 {' '.join(rpms)}"
            else:
                raise ValueError("Unsupported rpm based platform")
            
            err = self.system(command)
            if err and self._yum and self.downgradeAllowed():
                err = self.run(f"yum -y downgrade {' '.join(rpms)}")
            
            if err:
                raise RuntimeError("Failed to install glpi-agent")
            self._installed = rpms
        else:
            self._installed = 1
        
        # Call parent installer
        super().install()
    
    def uninstall(self):
        """Uninstall RPM packages"""
        rpms = sorted(self._packages.keys())
        
        if not rpms:
            self.info("glpi-agent is not installed")
            return
        
        self.uninstall_service()
        
        if len(rpms) == 1:
            self.info("Uninstalling glpi-agent package...")
        else:
            self.info(f"Uninstalling {len(rpms)} glpi-agent related packages...")
        
        err = self.run(f"rpm -e {' '.join(rpms)}")
        if err:
            raise RuntimeError("Failed to uninstall glpi-agent")
        
        for rpm in rpms:
            del self._packages[rpm]
    
    def clean(self):
        """Clean RPM-specific files"""
        super().clean()
        
        if os.path.exists("/etc/sysconfig/glpi-agent"):
            os.unlink("/etc/sysconfig/glpi-agent")
    
    def install_service(self):
        """Install service - handle both systemd and init.d"""
        if self.which("systemctl"):
            return super().install_service()
        
        if not (self.which("chkconfig") and self.which("service") and os.path.isdir("/etc/rc.d/init.d")):
            return self.info("Failed to enable glpi-agent service: unsupported distro")
        
        self.info("Enabling glpi-agent service using init file...")
        
        self.verbose("Extracting init file ...")
        if not self._archive.extract("pkg/rpm/glpi-agent.init.redhat"):
            raise IOError("Failed to extract glpi-agent.init.redhat")
        
        self.verbose("Installing init file ...")
        self.system("mv -vf glpi-agent.init.redhat /etc/rc.d/init.d/glpi-agent")
        self.system("chmod +x /etc/rc.d/init.d/glpi-agent")
        
        result = subprocess.run(['chkconfig', '--list', 'glpi-agent'], capture_output=True, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            self.system("chkconfig --add glpi-agent")
        
        self.verbose("Trying to start service ...")
        self.run("service glpi-agent restart")
    
    def install_cron(self):
        """Install cron job for RPM"""
        # glpi-agent-cron package should have been installed
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
        
        # Finally update /etc/sysconfig/glpi-agent to enable cron mode
        self.verbose("Enabling glpi-agent cron mode...")
        ret = self.run("sed -i -e s/=none/=cron/ /etc/sysconfig/glpi-agent")
        if ret:
            self.info("Failed to update /etc/sysconfig/glpi-agent")
    
    def uninstall_service(self):
        """Uninstall service - handle both systemd and init.d"""
        if self.which("systemctl"):
            return super().uninstall_service()
        
        if not (self.which("chkconfig") and self.which("service") and os.path.isdir("/etc/rc.d/init.d")):
            return self.info("Failed to uninstall glpi-agent service: unsupported distro")
        
        self.info("Uninstalling glpi-agent service init script...")
        
        self.verbose("Trying to stop service ...")
        self.run("service glpi-agent stop")
        
        self.verbose("Uninstalling init file ...")
        result = subprocess.run(['chkconfig', '--list', 'glpi-agent'], capture_output=True, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            self.system("chkconfig --del glpi-agent")
        self.system("rm -vf /etc/rc.d/init.d/glpi-agent")

