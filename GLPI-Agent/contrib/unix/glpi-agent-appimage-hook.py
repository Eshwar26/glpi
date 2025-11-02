#!/usr/bin/env python3
"""GLPI Agent AppImage Hook - Python version"""

import os
import sys
import re
import shutil
import subprocess
import stat
import glob
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

try:
    from GLPI.Agent.version import VERSION
except ImportError:
    VERSION = "unknown"

appdir = os.environ.get('APPDIR')
if not appdir:
    print("No APPDIR in environment", file=sys.stderr)
    sys.exit(1)

appdir = appdir.rstrip('/')

scripts = {
    'glpi-agent': True,
    'glpi-esx': True,
    'glpi-injector': True,
    'glpi-inventory': True,
    'glpi-netdiscovery': True,
    'glpi-netinventory': True,
    'glpi-remote': True,
    'glpi-agent-uninstall': True,
}

script = os.environ.get('GLPIAGENT_SCRIPT')
if script and script in scripts:
    # Run script asap unless called as installer or uninstaller
    if 'install' not in script and os.access(f"{appdir}/usr/bin/{script}", os.X_OK):
        os.execv(f"{appdir}/usr/bin/perl", ["perl", f"{appdir}/usr/bin/{script}"] + sys.argv[1:])
        print(f"Failed to run '{script}'", file=sys.stderr)
        sys.exit(1)

if '--perl' in sys.argv:
    args = [arg for arg in sys.argv[1:] if arg != '--perl']
    os.execv(f"{appdir}/usr/bin/perl", ["perl"] + args)
    print(f"Failed to run 'perl {' '.join(args)}'", file=sys.stderr)
    sys.exit(1)

# Handle --script option
script_arg = None
remaining_args = []
i = 0
while i < len(sys.argv):
    arg = sys.argv[i]
    if arg.startswith('--script'):
        if '=' in arg:
            script_arg = arg.split('=', 1)[1]
        elif i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
            script_arg = sys.argv[i + 1]
            i += 1
        else:
            print("Not valid script option", file=sys.stderr)
            sys.exit(1)
        
        if script_arg and not os.path.exists(f"{appdir}/usr/bin/{script_arg}"):
            print(f"No such embedded '{script_arg}' script", file=sys.stderr)
            sys.exit(1)
        
        args = [a for a in sys.argv[1:] if not (a.startswith('--script') or a == script_arg)]
        os.execv(f"{appdir}/usr/bin/perl", ["perl", f"{appdir}/usr/bin/{script_arg}"] + args)
        print(f"Failed to run '{script_arg}'", file=sys.stderr)
        sys.exit(1)
    else:
        remaining_args.append(arg)
    i += 1

sys.argv = remaining_args

# Parse options using argparse
import argparse

parser = argparse.ArgumentParser(description='GLPI Agent AppImage Hook')
# Configuration options
parser.add_argument('--backend-collect-timeout', type=int)
parser.add_argument('--ca-cert-dir')
parser.add_argument('--ca-cert-file')
parser.add_argument('--color', action='store_true')
parser.add_argument('--conf-reload-interval', type=int)
parser.add_argument('--debug', action='count', default=0)
parser.add_argument('--delaytime', type=int)
parser.add_argument('--esx-itemtype')
parser.add_argument('--force', action='store_true')
parser.add_argument('--full-inventory-postpone', type=int)
parser.add_argument('--glpi-version')
parser.add_argument('--html', action='store_true')
parser.add_argument('--itemtype')
parser.add_argument('--json', action='store_true')
parser.add_argument('--lazy', action='store_true')
parser.add_argument('--listen', action='store_true')
parser.add_argument('--local', '-l')
parser.add_argument('--logger')
parser.add_argument('--logfacility')
parser.add_argument('--logfile')
parser.add_argument('--logfile-maxsize', type=int)
parser.add_argument('--no-category')
parser.add_argument('--no-httpd', action='store_true')
parser.add_argument('--no-ssl-check', action='store_true')
parser.add_argument('--no-compression', '-C', action='store_true')
parser.add_argument('--no-task')
parser.add_argument('--no-p2p', action='store_true')
parser.add_argument('--password')
parser.add_argument('--proxy')
parser.add_argument('--httpd-ip')
parser.add_argument('--httpd-port', type=int)
parser.add_argument('--httpd-trust')
parser.add_argument('--remote')
parser.add_argument('--remote-workers', type=int)
parser.add_argument('--required-category')
parser.add_argument('--scan-homedirs', action='store_true')
parser.add_argument('--scan-profiles', action='store_true')
parser.add_argument('--server', '-s')
parser.add_argument('--ssl-cert-file')
parser.add_argument('--ssl-fingerprint')
parser.add_argument('--tag', '-t')
parser.add_argument('--tasks')
parser.add_argument('--timeout', type=int)
parser.add_argument('--user')
parser.add_argument('--vardir')
# Installer options
parser.add_argument('--help', '-h', action='store_true')
parser.add_argument('--runnow', action='store_true')
parser.add_argument('--clean', action='store_true')
parser.add_argument('--config')
parser.add_argument('--installpath', '-i')
parser.add_argument('--silent', '-S', action='store_true')
parser.add_argument('--install', action='store_true')
parser.add_argument('--reinstall', action='store_true')
parser.add_argument('--uninstall', action='store_true')
parser.add_argument('--upgrade', action='store_true')
parser.add_argument('--service', type=int, nargs='?', const=1)
parser.add_argument('--no-service', action='store_true')
parser.add_argument('--cron')
parser.add_argument('--wait', type=int)
parser.add_argument('--script')
parser.add_argument('--version', action='store_true')

try:
    options = parser.parse_args()
except SystemExit:
    sys.exit(1)

if options.help:
    parser.print_help()
    sys.exit(0)

if options.version:
    print(f"GLPI Agent AppImage installer v{VERSION}")
    sys.exit(0)

# Check for root privileges
try:
    result = subprocess.run(['id', '-u'], capture_output=True, text=True)
    uid = int(result.stdout.strip())
    if uid != 0:
        print(f"GLPI Agent AppImage v{VERSION} can only be run as root when installing or uninstalling", file=sys.stderr)
        sys.exit(1)
except Exception:
    print("Could not verify root privileges", file=sys.stderr)
    sys.exit(1)

clean = options.clean
silent = options.silent
cron = options.cron or False

if cron and options.service:
    print("GLPI Agent can't be installed as service and cron task at the same time", file=sys.stderr)
    sys.exit(1)

# Check if we are upgrading a cron based installation
if not cron and options.upgrade and not options.service:
    if os.path.exists("/etc/cron.daily/glpi-agent"):
        cron = "daily"
        options.service = 0
    elif os.path.exists("/etc/cron.hourly/glpi-agent"):
        cron = "hourly"
        options.service = 0

service = options.service if options.service is not None else (1 if not options.no_service else 0)
runnow = options.runnow
installpath = options.installpath
configpath = options.config or ''

if configpath and not os.path.exists(configpath):
    print(f"Wrong configuration path: {configpath} file doesn't exist", file=sys.stderr)
    sys.exit(1)

install = options.install
uninstall = options.uninstall or (script == "glpi-agent-uninstall")
reinstall = options.reinstall
upgrade = options.upgrade
wait = options.wait or 0

install = uninstall = True if (reinstall or upgrade) else install
clean = True if reinstall else clean

if not (install or reinstall or uninstall):
    print("One of --install, --upgrade, --reinstall or --uninstall options is mandatory", file=sys.stderr)
    sys.exit(1)

# Check mandatory option
mandatory = not install or (options.server or options.local)
vardir = options.vardir

# Build writeconf from options
writeconf = {}
for key, value in vars(options).items():
    if value is not None and key not in ['help', 'version', 'clean', 'silent', 'cron', 'runnow', 
                                         'installpath', 'config', 'install', 'uninstall', 'reinstall', 
                                         'upgrade', 'wait', 'script', 'service', 'no_service', 'vardir']:
        writeconf[key.replace('_', '-')] = value

# Read installed configuration
if os.path.isdir("/etc/glpi-agent/conf.d"):
    config = {}
    confs = glob.glob("/etc/glpi-agent/conf.d/*.cfg")
    confs.insert(0, "/etc/glpi-agent/agent.cfg")
    if configpath:
        confs.append(configpath)
    
    for conf in confs:
        if os.path.isfile(conf):
            try:
                with open(conf, 'r') as f:
                    for line in f:
                        line = line.strip()
                        match = re.match(r'^([a-z-]+)\s*=\s*(\S+.*)\s*$', line)
                        if match:
                            key = match.group(1)
                            value = match.group(2) or ""
                            config[key] = value
            except Exception:
                pass
    
    # Cleanup writeconf from values still defined in configuration
    if not clean:
        for key in list(writeconf.keys()):
            if key in config and writeconf[key] == config[key]:
                del writeconf[key]
                if options.debug:
                    print(f"{key} still in configuration")
    
    # Complete mandatory check
    mandatory = config.get('server') or config.get('local') or mandatory
    if not mandatory:
        mandatory = not reinstall
    
    # Keep vardir if found in conf
    if not vardir and 'vardir' in config:
        vardir = config['vardir']

if not mandatory:
    print("One of --server or --local options is mandatory while installing", file=sys.stderr)
    sys.exit(1)


def info(*messages):
    """Print info messages"""
    if silent:
        return
    for msg in messages:
        print(msg)


def copy_file(from_path, to_path, mode=None):
    """Copy file with optional mode"""
    if os.path.isdir(to_path):
        to_path = to_path.rstrip('/')
        name = os.path.basename(from_path)
        to_path = os.path.join(to_path, name)
    
    try:
        shutil.copy2(from_path, to_path)
        if mode:
            os.chmod(to_path, mode)
    except Exception as e:
        print(f"Can't copy {from_path} to {to_path}: {e}", file=sys.stderr)
        sys.exit(1)


vardir = vardir or "/var/lib/glpi-agent"

appimage = None
installpath_from_file = None

if os.path.exists(f"{vardir}/.INSTALLPATH") and not installpath:
    try:
        with open(f"{vardir}/.INSTALLPATH", 'r') as f:
            installpath_from_file = f.readline().strip()
    except Exception:
        pass

if os.path.exists(f"{vardir}/.APPIMAGE"):
    try:
        with open(f"{vardir}/.APPIMAGE", 'r') as f:
            appimage = f.readline().strip()
    except Exception:
        pass

# Fallback to default
installpath = installpath or installpath_from_file or "/usr/local/bin"

if not os.path.isdir(installpath):
    try:
        os.makedirs(installpath, exist_ok=True)
    except Exception as e:
        print(f"Can't create installation path: {e}", file=sys.stderr)
        sys.exit(1)

# Check service status
active = None
systemd = os.access("/usr/bin/systemctl", os.X_OK) and os.path.isdir("/etc/systemd/system")
if systemd:
    result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'glpi-agent'], 
                          capture_output=True, text=True, stderr=subprocess.DEVNULL)
    active = result.stdout.strip()
    if active == "active":
        info("Stopping glpi-agent service...") if options.debug else None
        cmd = "/usr/bin/systemctl stop glpi-agent"
        if silent:
            cmd += " >/dev/null 2>&1"
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print("Can't stop glpi-agent service", file=sys.stderr)
            sys.exit(1)
    else:
        active = None
elif os.path.exists("/etc/init.d/glpi-agent"):
    info("Stopping glpi-agent service...") if options.debug else None
    cmd = "/etc/init.d/glpi-agent stop"
    if silent:
        cmd += " >/dev/null 2>&1"
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("Can't stop glpi-agent service", file=sys.stderr)
        sys.exit(1)

if uninstall:
    info("Upgrading..." if upgrade else "Uninstalling...")
    
    for scriptfile in scripts.keys():
        script_path = os.path.join(installpath, scriptfile)
        if os.path.exists(script_path):
            try:
                os.unlink(script_path)
            except Exception as e:
                print(f"Can't remove dedicated {scriptfile} script: {e}", file=sys.stderr)
                sys.exit(1)
    
    if systemd:
        if active:
            cmd = "/usr/bin/systemctl disable glpi-agent"
            if silent:
                cmd += " >/dev/null 2>&1"
            subprocess.run(cmd, shell=True)
        
        service_file = "/etc/systemd/system/glpi-agent.service"
        if os.path.exists(service_file):
            os.unlink(service_file)
            cmd = "/usr/bin/systemctl daemon-reload"
            if silent:
                cmd += " >/dev/null 2>&1"
            subprocess.run(cmd, shell=True)
    elif os.path.exists("/etc/init.d/glpi-agent"):
        os.unlink("/etc/init.d/glpi-agent")
        for rc_file in glob.glob("/etc/rc*.d/*glpi-agent"):
            os.unlink(rc_file)
    
    if os.path.exists("/etc/cron.daily/glpi-agent"):
        os.unlink("/etc/cron.daily/glpi-agent")
    if os.path.exists("/etc/cron.hourly/glpi-agent"):
        os.unlink("/etc/cron.hourly/glpi-agent")
    
    if clean:
        info("Cleaning...")
        if os.path.isdir("/etc/glpi-agent"):
            info("Removing configurations in /etc/glpi-agent...")
            shutil.rmtree("/etc/glpi-agent", ignore_errors=True)
        if os.path.isdir(vardir):
            info(f"Removing {vardir}...")
            shutil.rmtree(vardir, ignore_errors=True)
        if os.path.exists("/var/log/glpi-agent.cron.log"):
            os.unlink("/var/log/glpi-agent.cron.log")
    
    # Remove current AppImage while upgrading with a newer AppImage
    if appimage and os.environ.get('APPIMAGE') and appimage != os.environ.get('APPIMAGE'):
        if os.path.exists(appimage):
            os.unlink(appimage)
        if os.path.exists(f"{vardir}/.APPIMAGE"):
            os.unlink(f"{vardir}/.APPIMAGE")
    
    # Also remove AppImage file unless re-installing
    if not install:
        if script and script == "glpi-agent-uninstall" and os.environ.get('APPIMAGE') and os.path.exists(os.environ.get('APPIMAGE')):
            os.unlink(os.environ.get('APPIMAGE'))
        elif not os.environ.get('APPIMAGE') and os.path.exists(f"{appdir}/glpi-agent.png"):
            # Support clean uninstall on systems where the App was extracted manually
            shutil.rmtree(appdir, ignore_errors=True)
    
    if os.path.exists(f"{vardir}/.INSTALLPATH"):
        os.unlink(f"{vardir}/.INSTALLPATH")

if install:
    info(f"Installing GLPI Agent v{VERSION}...")
    
    scripthook = None
    if os.environ.get('APPIMAGE'):
        filename = os.path.basename(os.environ.get('APPIMAGE'))
        scripthook = os.path.join(installpath, filename)
        
        # Only copy AppImage if not the same and still not present
        appimage_env = os.environ.get('APPIMAGE')
        if scripthook != appimage_env:
            if not os.path.exists(scripthook):
                info(f"Copying AppImage to {installpath}...")
                copy_file(appimage_env, scripthook, 0o755)
            else:
                # Compare files
                try:
                    result = subprocess.run(['cmp', '-s', scripthook, appimage_env], 
                                          capture_output=True, stderr=subprocess.DEVNULL)
                    if result.returncode != 0:
                        info(f"Copying AppImage to {installpath}...")
                        copy_file(appimage_env, scripthook, 0o755)
                except Exception:
                    pass
    elif os.path.exists(f"{appdir}/AppRun"):
        scripthook = f"{appdir}/AppRun"
    
    if not scripthook:
        print("Failed to set script hook program", file=sys.stderr)
        sys.exit(1)
    
    for scriptfile in scripts.keys():
        script_path = os.path.join(installpath, scriptfile)
        try:
            with open(script_path, 'w') as f:
                f.write("#!/bin/sh\n")
                f.write(f"export GLPIAGENT_SCRIPT={scriptfile}\n")
                f.write(f"exec '{scripthook}' $*\n")
            os.chmod(script_path, 0o755)
        except Exception as e:
            print(f"Failed to create dedicated '{scriptfile}' script: {e}", file=sys.stderr)
            sys.exit(1)
    
    info("Configuring...")
    if clean and os.path.isdir("/etc/glpi-agent"):
        shutil.rmtree("/etc/glpi-agent", ignore_errors=True)
    
    os.makedirs("/etc/glpi-agent/conf.d", exist_ok=True)
    
    # Copy configuration files
    etc_configs = glob.glob(f"{appdir}/usr/share/glpi-agent/etc/*.cfg")
    for conf in etc_configs:
        copy_file(conf, "/etc/glpi-agent")
    
    configs = glob.glob(f"{appdir}/config/*.cfg")
    if configpath:
        configs.append(configpath)
    
    for conf in configs:
        copy_file(conf, "/etc/glpi-agent/conf.d")
    
    # Write new configuration
    if writeconf:
        index = -1
        conf_file = None
        while index < 100:
            index += 1
            conf_file = f"/etc/glpi-agent/conf.d/{index:02d}-install.cfg"
            if not os.path.exists(conf_file):
                break
        
        info(f"Writing configuration in {conf_file} ...")
        try:
            with open(conf_file, 'w') as f:
                for key in sorted(writeconf.keys()):
                    value = writeconf[key]
                    f.write(f"{key} = {value}\n")
        except Exception as e:
            print(f"Failed to write configuration: {e}", file=sys.stderr)
            sys.exit(1)
    
    if clean and os.path.isdir(vardir):
        shutil.rmtree(vardir, ignore_errors=True)
    os.makedirs(vardir, exist_ok=True)
    
    # Keep installed install path in VARDIR
    try:
        with open(f"{vardir}/.INSTALLPATH", 'w') as f:
            f.write(f"{installpath}\n")
    except Exception:
        pass
    
    # Keep installed AppImage in VARDIR
    try:
        with open(f"{vardir}/.APPIMAGE", 'w') as f:
            f.write(f"{scripthook}\n")
    except Exception:
        pass
    
    # Runnow support
    if runnow:
        if service:
            result = subprocess.run([f"{appdir}/usr/bin/perl", "perl", f"{appdir}/usr/bin/glpi-agent", "--set-forcerun"])
            if result.returncode != 0:
                print("Failed to force inventory on next glpi-agent start", file=sys.stderr)
                sys.exit(1)
        else:
            result = subprocess.run([f"{appdir}/usr/bin/perl", "perl", f"{appdir}/usr/bin/glpi-agent", "--force"])
            if result.returncode != 0:
                print("Failed to run glpi-agent", file=sys.stderr)
                sys.exit(1)
    
    # Install service
    if service:
        if systemd:
            reloaddaemon = os.path.exists("/etc/systemd/system/glpi-agent.service")
            
            # Copy glpi-agent.service fixing ExecStart
            service_src = f"{appdir}/lib/systemd/system/glpi-agent.service"
            service_dest = "/etc/systemd/system/glpi-agent.service"
            
            if os.path.exists(service_src):
                try:
                    with open(service_src, 'r') as fhr:
                        with open(service_dest, 'w') as fhw:
                            for line in fhr:
                                line = re.sub(r'^ExecStart=/usr/bin/glpi-agent', 
                                            f'ExecStart={installpath}/glpi-agent', line)
                                fhw.write(line)
                    
                    if reloaddaemon:
                        cmd = "/usr/bin/systemctl daemon-reload"
                        if silent:
                            cmd += " >/dev/null 2>&1"
                        subprocess.run(cmd, shell=True)
                    
                    cmd = "/usr/bin/systemctl enable glpi-agent"
                    if silent:
                        cmd += " >/dev/null 2>&1"
                    result = subprocess.run(cmd, shell=True)
                    if result.returncode != 0:
                        print("Failed to enable glpi-agent service", file=sys.stderr)
                        sys.exit(1)
                    
                    cmd = "/usr/bin/systemctl reload-or-restart glpi-agent"
                    if silent:
                        cmd += " >/dev/null 2>&1"
                    result = subprocess.run(cmd, shell=True)
                    if result.returncode != 0:
                        print("Failed to start glpi-agent service", file=sys.stderr)
                        sys.exit(1)
                except Exception as e:
                    print(f"Failed to install service: {e}", file=sys.stderr)
                    sys.exit(1)
        elif os.path.isdir("/etc/init.d"):
            # Copy /etc/init.d/glpi-agent fixing installpath
            init_src = f"{appdir}/etc/init.d/glpi-agent"
            init_dest = "/etc/init.d/glpi-agent"
            
            if os.path.exists(init_src):
                try:
                    with open(init_src, 'r') as fhr:
                        with open(init_dest, 'w') as fhw:
                            for line in fhr:
                                line = re.sub(r'^installpath=/usr/local/bin$', 
                                            f'installpath={installpath}', line)
                                fhw.write(line)
                    
                    os.chmod(init_dest, 0o755)
                    
                    cmd = "/etc/init.d/glpi-agent start"
                    if silent:
                        cmd += " >/dev/null 2>&1"
                    result = subprocess.run(cmd, shell=True)
                    if result.returncode != 0:
                        print("Failed to start glpi-agent service", file=sys.stderr)
                        sys.exit(1)
                    
                    # Install rc links
                    for rc in range(7):
                        link_name = "K01glpi-agent" if (rc < 2 or rc > 5) else "S99glpi-agent"
                        link_path = f"/etc/rc{rc}.d/{link_name}"
                        try:
                            if os.path.exists(link_path):
                                os.unlink(link_path)
                            os.symlink("../init.d/glpi-agent", link_path)
                        except Exception as e:
                            print(f"Can't create {link_path} symbolic link: {e}", file=sys.stderr)
                            sys.exit(1)
                except Exception as e:
                    print(f"Failed to install init script: {e}", file=sys.stderr)
                    sys.exit(1)
    elif cron:
        if cron == "daily":
            cronfile = "/etc/cron.daily/glpi-agent"
        elif cron == "hourly":
            cronfile = "/etc/cron.hourly/glpi-agent"
        else:
            print("--cron option can only be set to 'hourly' or 'daily'", file=sys.stderr)
            sys.exit(1)
        
        wait_opt = ""
        if wait:
            if not isinstance(wait, int) or wait < 0:
                print("invalid --wait option value: it must be a delay integer value in seconds", file=sys.stderr)
                sys.exit(1)
            elif cron == "hourly" and wait >= 3600:
                print("--wait option value must be lower than 3600 for hourly cron mode", file=sys.stderr)
                sys.exit(1)
            elif cron == "daily" and wait >= 86400:
                print("--wait option value must be lower than 86400 for daily cron mode", file=sys.stderr)
                sys.exit(1)
            else:
                wait_opt = f"--wait {wait} "
        
        try:
            with open(cronfile, 'w') as f:
                f.write("#!/bin/sh\n")
                f.write(f"exec '{installpath}/glpi-agent' {wait_opt}>/var/log/glpi-agent.cron.log 2>&1\n")
            os.chmod(cronfile, 0o755)
        except Exception as e:
            print(f"Failed to write {cron} cron file: {e}", file=sys.stderr)
            sys.exit(1)


