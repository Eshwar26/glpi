#!/usr/bin/env python3
"""LinuxDistro - Linux distribution detection and installation management"""

import os
import re
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# Distribution definitions: [release_file, name, version_regex, template, packaging_class]
DISTRIBUTIONS = [
    # vmware-release contains something like "VMware ESX Server 3" or "VMware ESX 4.0 (Kandinsky)"
    ['/etc/vmware-release', 'VMWare', r'([\d.]+)', '%s'],
    
    ['/etc/arch-release', 'ArchLinux', r'(.*)', 'ArchLinux'],
    
    ['/etc/debian_version', 'Debian', r'(.*)', 'Debian GNU/Linux %s', 'DebDistro'],
    
    # fedora-release contains something like "Fedora release 9 (Sulphur)"
    ['/etc/fedora-release', 'Fedora', r'release ([\d.]+)', '%s', 'RpmDistro'],
    
    ['/etc/gentoo-release', 'Gentoo', r'(.*)', 'Gentoo Linux %s'],
    
    # knoppix_version contains something like "3.2 2003-04-15"
    ['/etc/knoppix_version', 'Knoppix', r'(.*)', 'Knoppix GNU/Linux %s'],
    
    # mandriva-release contains something like "Mandriva Linux release 2010.1 (Official) for x86_64"
    ['/etc/mandriva-release', 'Mandriva', r'release ([\d.]+)', '%s'],
    
    # mandrake-release contains something like "Mandrakelinux release 10.1 (Community) for i586"
    ['/etc/mandrake-release', 'Mandrake', r'release ([\d.]+)', '%s'],
    
    # oracle-release contains something like "Oracle Linux Server release 6.3"
    ['/etc/oracle-release', 'Oracle Linux Server', r'release ([\d.]+)', '%s', 'RpmDistro'],
    
    # rocky-release contains something like "Rocky Linux release 8.5 (Green Obsidian)"
    ['/etc/rocky-release', 'Rocky Linux', r'release ([\d.]+)', '%s', 'RpmDistro'],
    
    # almalinux-release contains something like "AlmaLinux release 9.2 (Turquoise Kodkod)"
    ['/etc/almalinux-release', 'AlmaLinux', r'release ([\d.]+)', '%s', 'RpmDistro'],
    
    # centos-release contains something like "CentOS Linux release 6.0 (Final)"
    ['/etc/centos-release', 'CentOS', r'release ([\d.]+)', '%s', 'RpmDistro'],
    
    # redhat-release contains something like "Red Hat Enterprise Linux Server release 5 (Tikanga)"
    ['/etc/redhat-release', 'RedHat', r'release ([\d.]+)', '%s', 'RpmDistro'],
    
    ['/etc/slackware-version', 'Slackware', r'Slackware (.*)', '%s'],
    
    # SuSE-release contains something like "SUSE Linux Enterprise Server 11 (x86_64)"
    ['/etc/SuSE-release', 'SuSE', r'([\d.]+)', '%s', 'RpmDistro'],
    
    # trustix-release contains something like "Trustix Secure Linux release 2.0 (Cloud)"
    ['/etc/trustix-release', 'Trustix', r'release ([\d.]+)', '%s'],
    
    # Fallback
    ['/etc/issue', 'Unknown Linux distribution', r'([\d.]+)', '%s'],
]

# Class matching based on /etc/os-release
CLASSES = {
    'DebDistro': re.compile(r'debian|ubuntu', re.IGNORECASE),
    'RpmDistro': re.compile(r'red\s?hat|centos|fedora|opensuse|almalinux|rocky|oracle', re.IGNORECASE),
}


class LinuxDistro:
    """Base class for Linux distribution management"""
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """
        Initialize distribution handler.
        
        Args:
            options: Dictionary of installer options
        """
        if options is None:
            options = {}
        
        self._bin = "/usr/bin/glpi-agent"
        self._silent = options.pop('silent', 0)
        self._verbose = options.pop('verbose', 0)
        self._service = options.pop('service', None)  # checked later against cron
        self._cron = options.pop('cron', 0)
        self._runnow = options.pop('runnow', 0)
        self._dont_ask = options.pop('no-question', 0)
        self._type = options.pop('type', None)
        self._user_proxy = options.pop('use-current-user-proxy', 0)
        self._options = options
        self._cleanpkg = 1
        self._skip = {}
        self._downgrade = 0
        self.base_folder = None  # For testing
        self._fh = None
        self._fh_file = None
        self._packages = {}
        self._archive = None
        self._installed = None
    
    def analyze(self):
        """Analyze and detect Linux distribution"""
        options = self._options
        
        distro = options.pop('distro', None)
        force = options.pop('force', False)
        snap = options.pop('snap', 0)
        
        name, version, release, class_name = self._getDistro()
        
        if force:
            if distro:
                name = distro
            if not version:
                version = "unknown version"
            if not distro:
                release = "unknown distro"
            
            # Determine class from name
            for cls, pattern in CLASSES.items():
                if pattern.search(name):
                    class_name = cls
                    break
            
            self.allowDowngrade()
        
        self._name = name
        self._version = version
        self._release = release
        
        if snap:
            class_name = "SnapInstall"
        
        if not name or not version or not release:
            raise ValueError("Not supported linux distribution")
        
        if not class_name:
            raise ValueError(f"Unsupported {release} linux distribution ({name}:{version})")
        
        self.verbose(f"Running on linux distro: {release} : {name} : {version}...")
        
        # Service is mandatory when set with cron option
        if self._service is None:
            self._service = 0 if self._cron else 1
        elif self._cron:
            self.info("Disabling cron as --service option is used")
            self._cron = 0
        
        # Handle package skipping option
        skip = options.pop('skip', None)
        if skip:
            for pkg in skip.split(','):
                if pkg:
                    self._skip[pkg] = True
        
        # Re-bless to specific distro class
        # In Python, we'll dynamically change the class
        if class_name == 'DebDistro':
            self.__class__ = DebDistro
        elif class_name == 'RpmDistro':
            self.__class__ = RpmDistro
        elif class_name == 'SnapInstall':
            self.__class__ = SnapInstall
    
    def init(self):
        """Initialize distribution-specific settings"""
        if self._type is None:
            self._type = "typical"
    
    def installed(self) -> Optional[str]:
        """Get installed version"""
        if self._packages:
            return list(self._packages.values())[0]
        return None
    
    def info(self, *messages):
        """Print info messages"""
        if self._silent:
            return
        for msg in messages:
            print(msg)
    
    def verbose(self, *messages):
        """Print verbose messages"""
        if messages and self._verbose:
            self.info(*messages)
        return self._verbose and not self._silent
    
    def open_os_file(self, filepath: str, mode: str = 'r'):
        """
        Open OS file.
        
        Args:
            filepath: File path to open
            mode: File open mode
            
        Returns:
            File handle
        """
        if self._fh and self._fh_file:
            raise IOError(f"Can't open another system file: {self._fh_file} still opened")
        
        # base_folder is used for tests
        if self.base_folder:
            full_path = os.path.join(self.base_folder, filepath.lstrip('/'))
        else:
            full_path = filepath
        
        if mode == '>':
            self._fh = open(full_path, 'w')
        else:
            self._fh = open(full_path, 'r')
        
        self._fh_file = filepath
        return self._fh
    
    def close_os_file(self):
        """Close OS file"""
        if self._fh:
            self._fh.close()
            self._fh = None
        self._fh_file = None
    
    def chmod_os_file(self, mode: int, filepath: str):
        """
        Change file permissions.
        
        Args:
            mode: Permission mode (octal)
            filepath: File path
        """
        if self.base_folder:
            full_path = os.path.join(self.base_folder, filepath.lstrip('/'))
        else:
            full_path = filepath
        os.chmod(full_path, mode)
    
    def os_file_exists(self, filepath: str) -> bool:
        """
        Check if OS file exists.
        
        Args:
            filepath: File path to check
            
        Returns:
            True if file exists, False otherwise
        """
        if self.base_folder:
            full_path = os.path.join(self.base_folder, filepath.lstrip('/'))
        else:
            full_path = filepath
        return os.path.exists(full_path)
    
    def _getDistro(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Detect Linux distribution.
        
        Returns:
            Tuple of (name, version, release, class_name)
        """
        osreleasefile = '/etc/os-release'
        
        if self.os_file_exists(osreleasefile):
            try:
                handle = self.open_os_file(osreleasefile)
                
                name = None
                version = None
                description = None
                class_name = None
                
                for line in handle:
                    line = line.strip()
                    match = re.match(r'^NAME="?([^"]+)"?', line)
                    if match:
                        name = match.group(1)
                        if 'REDHAT_' in line:
                            class_name = 'RpmDistro'
                    elif not name and re.match(r'^REDHAT_SUPPORT_PRODUCT="?([^"]+)"?', line):
                        match = re.match(r'^REDHAT_SUPPORT_PRODUCT="?([^"]+)"?', line)
                        if match:
                            name = match.group(1)
                            class_name = 'RpmDistro'
                    elif re.match(r'^VERSION="?([^"]+)"?', line):
                        match = re.match(r'^VERSION="?([^"]+)"?', line)
                        if match:
                            version = match.group(1)
                    elif not version:
                        match = re.match(r'^VERSION_ID="?([^"]+)"?', line)
                        if match:
                            version = match.group(1)
                        else:
                            match = re.match(r'^REDHAT_SUPPORT_PRODUCT_VERSION="?([^"]+)"?', line)
                            if match:
                                version = match.group(1)
                    elif re.match(r'^PRETTY_NAME="?([^"]+)"?', line):
                        match = re.match(r'^PRETTY_NAME="?([^"]+)"?', line)
                        if match:
                            description = match.group(1)
                
                self.close_os_file()
                
                # Determine class from name if not set
                if not class_name and name:
                    for cls, pattern in CLASSES.items():
                        if pattern.search(name):
                            class_name = cls
                            break
                
                # For RpmDistro, try to get description from redhat-release
                if class_name == 'RpmDistro' and not description and self.os_file_exists('/etc/redhat-release'):
                    try:
                        handle = self.open_os_file('/etc/redhat-release')
                        description = handle.readline().strip()
                        self.close_os_file()
                    except:
                        pass
                
                if class_name:
                    return (name, version, description or name, class_name)
            
            except Exception:
                pass
        
        # Otherwise analyze first line of distribution files
        for distro_spec in DISTRIBUTIONS:
            filepath = distro_spec[0]
            if self.os_file_exists(filepath):
                name = distro_spec[1]
                version_regex = distro_spec[2]
                template = distro_spec[3]
                class_name = distro_spec[4] if len(distro_spec) > 4 else None
                
                self.verbose(f"Found distro: {name}")
                
                try:
                    handle = self.open_os_file(filepath)
                    line = handle.readline().strip()
                    self.close_os_file()
                    
                    # Arch Linux has an empty release file
                    if line:
                        release = template % line
                        match = re.search(version_regex, line)
                        version = match.group(1) if match else None
                    else:
                        release = template
                        version = None
                    
                    return (name, version, release, class_name)
                
                except Exception as e:
                    self.verbose(f"Error reading {filepath}: {e}")
        
        return (None, None, None, None)
    
    def extract(self, archive, extract: Optional[str]):
        """Extract packages from archive"""
        self._archive = archive
        
        if extract is None:
            return
        
        if extract == "keep":
            self.info("Will keep extracted packages")
            self._cleanpkg = 0
            return
        
        self.info(f"Extracting {extract} packages...")
        pkgs = [p for p in extract.split(',') if p in ['rpm', 'deb', 'snap']]
        pkg_pattern = '\\w+' if extract == "all" else '|'.join(pkgs)
        
        if pkg_pattern:
            count = 0
            for name in archive.files():
                match = re.match(rf'^pkg/(?:{pkg_pattern})/(.+)$', name)
                if match:
                    dest = match.group(1)
                    self.verbose(f"Extracting {name} to {dest}")
                    if not archive.extract(name):
                        raise IOError(f"Failed to extract {name}")
                    count += 1
            
            self.info(f"{count} extracted package{'s' if count != 1 else ''}" if count else "No package extracted")
        else:
            self.info("Nothing to extract")
        
        sys.exit(0)
    
    def getDeps(self, ext: str) -> List[str]:
        """Get dependency packages for given extension"""
        if not self._archive or not ext:
            return []
        
        pkgs = []
        count = 0
        for name in self._archive.files():
            match = re.match(rf'^pkg/{ext}/deps/(.+)$', name)
            if match:
                dep_name = match.group(1)
                self.verbose(f"Extracting {ext} deps {dep_name}")
                if not self._archive.extract(dep_name):
                    raise IOError(f"Failed to extract {dep_name}")
                count += 1
                pkgs.append(dep_name)
        
        if count:
            self.info(f"{count} extracted {ext} deps package{'s' if count != 1 else ''}")
        
        return pkgs
    
    def configure(self, folder: Optional[str] = None):
        """Configure agent"""
        if folder is None:
            folder = "/etc/glpi-agent/conf.d"
        
        # Check if configuration exists in archive
        configs = [f for f in self._archive.files() if re.match(r'^config/[^/]+\.(cfg|crt|pem)$', f)]
        
        # Check existing installed config
        installed_config = f"{folder}/00-install.cfg"
        current_config = None
        if self.os_file_exists(installed_config) and not self._options:
            configs.append(installed_config)
            try:
                fh = self.open_os_file(installed_config)
                current_config = fh.readline()
                self.close_os_file()
            except:
                pass
        
        # Ask configuration unless in silent mode
        if not self._silent and not self._dont_ask and not (self._options.get('server') or self._options.get('local')):
            cfg_files = [c for c in configs if c.endswith('.cfg')]
            if cfg_files:
                for cfg in cfg_files:
                    content = current_config if cfg == installed_config else self._archive.content(cfg)
                    if content and isinstance(content, bytes):
                        content = content.decode('utf-8', errors='ignore')
                    if content and re.search(r'^(server|local)\s*=\s*\S', content, re.MULTILINE):
                        self._dont_ask = 1
                        break
            
            if not self._dont_ask:
                self.ask_configure()
        
        # Check to use current user proxy environment
        if not self._options.get('proxy') and self._user_proxy:
            proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
            if proxy:
                self._options['proxy'] = proxy
        
        if self._options:
            self.info("Applying configuration...")
            if not os.path.isdir(folder):
                raise IOError(f"Can't apply configuration without {folder} folder")
            
            fh = self.open_os_file(installed_config, '>')
            self.verbose(f"Writing configuration in {installed_config}")
            for option in sorted(self._options.keys()):
                value = self._options.get(option) or ""
                self.verbose(f"Adding: {option} = {value}")
                fh.write(f"{option} = {value}\n")
            
            self.close_os_file()
        else:
            if not configs:
                self.info("No configuration to apply")
        
        # Install config files from archive
        for config in configs:
            if config == installed_config:
                continue
            
            match = re.match(r'^config/([^/]+\.(?:cfg|crt|pem))$', config)
            if match:
                cfg = match.group(1)
                if not os.path.isdir(folder):
                    raise IOError(f"Can't install {cfg} configuration without {folder} folder")
                self.info(f"Installing {cfg} config in {folder}")
                dest = os.path.join(folder, cfg)
                if os.path.exists(dest):
                    os.unlink(dest)
                self._archive.extract(config, dest)
    
    def ask_configure(self):
        """Interactively ask for configuration"""
        self.info(f"glpi-agent is about to be installed as {'service' if self._service else 'cron task'}")
        
        if 'server' in self._options:
            if self._options['server']:
                self.info(f"GLPI server will be configured to: {self._options['server']}")
            else:
                self.info("Disabling server configuration")
        else:
            print("\nProvide an url to configure GLPI server:\n> ", end='', flush=True)
            server = sys.stdin.readline().strip()
            if server:
                self._options['server'] = server
        
        if 'local' in self._options:
            if not os.path.isdir(self._options['local']):
                self.info(f"Not existing local inventory path, clearing: {self._options['local']}")
                del self._options['local']
            elif self._options['local']:
                self.info(f"Local inventory path will be configured to: {self._options['local']}")
            else:
                self.info("Disabling local inventory")
        
        while 'local' not in self._options:
            print("\nProvide a path to configure local inventory run or leave it empty:\n> ", end='', flush=True)
            local = sys.stdin.readline().strip()
            if not local:
                break
            if os.path.isdir(local):
                self._options['local'] = local
            else:
                self.info(f"Not existing local inventory path: {local}")
        
        if 'tag' in self._options:
            if self._options['tag']:
                self.info(f"Inventory tag will be configured to: {self._options['tag']}")
            else:
                self.info("Using empty inventory tag")
        else:
            print("\nProvide a tag to configure or leave it empty:\n> ", end='', flush=True)
            tag = sys.stdin.readline().strip()
            if tag:
                self._options['tag'] = tag
    
    def install(self):
        """Install agent"""
        if not self._installed:
            raise ValueError(f"Install not supported on {self._release} linux distribution ({self._name}:{self._version})")
        
        self.configure()
        
        if self._service:
            self.install_service()
            
            if self._runnow:
                import time
                time.sleep(1)
                self.info("Asking service to run inventory now as requested...")
                self.system("systemctl -s SIGUSR1 kill glpi-agent")
        elif self._cron:
            self.install_cron()
            
            if self._runnow:
                self.info("Running inventory now as requested...")
                self.system(self._bin)
        
        self.clean_packages()
    
    def clean(self):
        """Clean agent files"""
        if self._packages:
            raise ValueError("Can't clean glpi-agent related files if it is currently installed")
        self.info("Cleaning...")
        self.run("rm -rf /etc/glpi-agent /var/lib/glpi-agent")
    
    def run(self, command: str) -> int:
        """
        Run shell command.
        
        Returns:
            Exit code
        """
        if not command:
            return 0
        
        self.verbose(f"Running: {command}")
        cmd = command if self._verbose else command + " >/dev/null"
        result = subprocess.run(cmd, shell=True)
        
        if result.returncode == -1:
            raise IOError(f"Failed to run {command}")
        
        return result.returncode
    
    def uninstall(self):
        """Uninstall agent - must be overridden"""
        raise ValueError(f"Uninstall not supported on {self._release} linux distribution ({self._name}:{self._version})")
    
    def install_service(self):
        """Install as systemd service"""
        self.info("Enabling glpi-agent service...")
        
        # Always stop service if necessary
        isactivecmd = "systemctl is-active glpi-agent"
        if not self._verbose:
            isactivecmd += " 2>/dev/null"
        
        result = subprocess.run(isactivecmd, shell=True, capture_output=True, text=True)
        if result.stdout.strip() == "active":
            self.system("systemctl stop glpi-agent")
        
        ret = self.run("systemctl enable glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to enable glpi-agent service")
            return
        
        self.verbose("Starting glpi-agent service...")
        ret = self.run("systemctl reload-or-restart glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to start glpi-agent service")
    
    def install_cron(self):
        """Install as cron job - must be overridden"""
        raise ValueError(f"Installing as cron is not supported on {self._release} linux distribution ({self._name}:{self._version})")
    
    def uninstall_service(self):
        """Uninstall systemd service"""
        self.info("Disabling glpi-agent service...")
        
        isactivecmd = "systemctl is-active glpi-agent"
        if not self._verbose:
            isactivecmd += " 2>/dev/null"
        
        result = subprocess.run(isactivecmd, shell=True, capture_output=True, text=True)
        if result.stdout.strip() == "active":
            self.system("systemctl stop glpi-agent")
        
        ret = self.run("systemctl disable glpi-agent" + ("" if self._verbose else " 2>/dev/null"))
        if ret:
            self.info("Failed to disable glpi-agent service")
    
    def clean_packages(self):
        """Clean extracted package files"""
        if self._cleanpkg and isinstance(self._installed, list):
            self.verbose("Cleaning extracted packages")
            for pkg in self._installed:
                if os.path.exists(pkg):
                    os.unlink(pkg)
            self._installed = None
    
    def allowDowngrade(self):
        """Allow package downgrade"""
        self._downgrade = 1
    
    def downgradeAllowed(self) -> bool:
        """Check if downgrade is allowed"""
        return self._downgrade
    
    def which(self, cmd: str) -> Optional[str]:
        """Find command in PATH"""
        result = subprocess.run(f"which {cmd}", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def system(self, cmd: str) -> int:
        """
        Run system command.
        
        Returns:
            Exit code
        """
        self.verbose(f"Running: {cmd}")
        cmd_full = cmd if self._verbose else cmd + " >/dev/null 2>&1"
        return subprocess.run(cmd_full, shell=True).returncode


# Import distribution classes
try:
    from .DebDistro import DebDistro
    from .RpmDistro import RpmDistro
    from .SnapInstall import SnapInstall
except ImportError:
    # Stub classes for type hints - actual implementations are in separate files
    class DebDistro(LinuxDistro):
        pass
    
    class RpmDistro(LinuxDistro):
        pass
    
    class SnapInstall(LinuxDistro):
        pass

