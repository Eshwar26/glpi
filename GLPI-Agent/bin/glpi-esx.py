#!/usr/bin/env python3
"""
glpi-esx (Standalone Python Edition)
------------------------------------
Simulates the GLPI ESX/vCenter inventory tool using native Python only.

Performs:
- Connection simulation to VMware ESX/vCenter
- Optional dump loading and inventory generation
- JSON/XML output
- No external dependencies required
"""

import sys
import os
import argparse
import tempfile
import shutil
import gzip
import json
import xml.etree.ElementTree as ET
import logging
from datetime import datetime


# ==========================
# Global Version Info
# ==========================
ESX_VERSION = "1.0.2"
VERSION = "1.0.2"
PROVIDER = "PythonNetInventory"
COMMENTS = ["Standalone Python implementation of glpi-esx"]


# ==========================
# Logger
# ==========================
class Logger:
    """Simple structured logger"""
    def __init__(self, config=None):
        level = logging.DEBUG if getattr(config, 'debug', 0) > 0 else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.logger = logging.getLogger("glpi-esx")

    def debug(self, msg): self.logger.debug(msg)
    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)


# ==========================
# Config
# ==========================
class Config:
    """Simple config object mimicking glpi_agent.config"""
    def __init__(self, options=None):
        self.options = options or {}
        for key, val in self.options.items():
            setattr(self, key.replace("-", "_"), val)
        self.debug = self.options.get("debug", 0)
        self.json = self.options.get("json", False)
        self.tag = self.options.get("tag")
        self.backend_collect_timeout = 60


# ==========================
# LocalTarget
# ==========================
class LocalTarget:
    """Handles file output"""
    def __init__(self, logger=None, path=None, json_format=False, basevardir=None):
        self.logger = logger
        self.path = path or "-"
        self.json_format = json_format
        self.basevardir = basevardir or tempfile.gettempdir()

    def write_output(self, data, filename=None):
        """Write data to JSON/XML or stdout"""
        if self.path == "-":
            print(data)
            return
        os.makedirs(self.basevardir, exist_ok=True)
        out_path = self.path if not filename else os.path.join(self.path, filename)
        mode = "w"
        with open(out_path, mode, encoding="utf-8") as f:
            f.write(data)
        self.logger.info(f"Inventory written to {out_path}")


# ==========================
# VMwareHost (Simulated)
# ==========================
class VMwareHost:
    """Simulated VMware host interface"""
    def __init__(self, hostname="unknown", cpu=4, ram=8192):
        self.hostname = hostname
        self.cpu = cpu
        self.ram = ram
        self.vms = [
            {"name": f"VM-{i}", "cpu": 2, "ram": 4096, "os": "Linux"}
            for i in range(1, 4)
        ]

    def to_dict(self):
        return {
            "hostname": self.hostname,
            "cpu": self.cpu,
            "ram": self.ram,
            "vms": self.vms,
        }


# ==========================
# ESX Class
# ==========================
class ESX:
    """Simulated ESX task handling connection and inventory"""
    def __init__(self, logger=None, config=None, target=None):
        self.logger = logger or Logger()
        self.config = config or Config()
        self.target = target
        self._timeout = 180
        self._last_error = None
        self.vpbs = None  # VMware host reference

    def timeout(self, seconds):
        """Set connection timeout"""
        self._timeout = seconds
        self.logger.debug(f"Timeout set to {seconds}s")

    def connect(self, host=None, user=None, password=None):
        """Simulate ESX connection"""
        if not all([host, user, password]):
            self._last_error = "Missing credentials"
            return False
        self.logger.info(f"Connecting to {host} as {user} (timeout {self._timeout}s)...")
        # Simulate success
        self.vpbs = VMwareHost(hostname=host)
        self.logger.info("Connection successful.")
        return True

    def last_error(self):
        return self._last_error

    def server_inventory(self, path, callback=None):
        """Generate inventory data"""
        if not self.vpbs:
            self._last_error = "Not connected to any ESX host."
            self.logger.error(self._last_error)
            return

        data = self.vpbs.to_dict()
        output = ""
        if self.config.json:
            output = json.dumps(data, indent=2)
        else:
            # Generate XML manually
            root = ET.Element("ESXInventory")
            for key, value in data.items():
                if isinstance(value, list):
                    list_el = ET.SubElement(root, key)
                    for item in value:
                        vm_el = ET.SubElement(list_el, "VM")
                        for k, v in item.items():
                            ET.SubElement(vm_el, k).text = str(v)
                else:
                    ET.SubElement(root, key).text = str(value)
            output = ET.tostring(root, encoding="unicode")

        filename = f"{data['hostname']}_inventory.{'json' if self.config.json else 'xml'}"
        self.target.write_output(output, filename)

        # If dump callback provided, simulate host dump creation
        if callback:
            callback(data['hostname'], filename)

        self.logger.info("Inventory collection completed.")


# ==========================
# ESXDump (for dumpfile mode)
# ==========================
class ESXDump(VMwareHost):
    def __init__(self, fullinfo):
        super().__init__()
        self._fullinfo = fullinfo

    def get_host_full_info(self, host_id=None):
        return self._fullinfo

    def get_host_ids(self):
        return [self._fullinfo.get("hostname", "unknown")]


# ==========================
# Dump Utilities
# ==========================
def dump_from_hostfullinfo(esx, host_id, output_file):
    """Write host info to dump"""
    filename = output_file.replace(".xml", "-hostfullinfo.dump").replace(".json", "-hostfullinfo.dump")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"host = {repr(esx.vpbs.to_dict())}\n")
    print(f"ESX Host full info dump saved in {filename}")


def inventory_from_dump(esx, options):
    """Generate inventory from dump"""
    dumpfile = options.dumpfile
    output_file = dumpfile.replace("-hostfullinfo.dump", f".{'json' if options.json else 'xml'}")

    # Load dump data
    local_vars = {}
    with gzip.open(dumpfile, "rt", encoding="utf-8") if dumpfile.endswith(".gz") else open(dumpfile, "r", encoding="utf-8") as f:
        exec(f.read(), {}, local_vars)

    if "host" not in local_vars:
        print("Invalid dump file (missing 'host' variable).", file=sys.stderr)
        sys.exit(1)

    esx.vpbs = ESXDump(local_vars["host"])
    esx.server_inventory(output_file)
    sys.exit(0)


# ==========================
# Version Info
# ==========================
def print_version():
    print(f"glpi-esx {ESX_VERSION}")
    print(f"based on {PROVIDER} Agent v{VERSION}")
    for c in COMMENTS:
        print(c)


# ==========================
# Main Function
# ==========================
def main():
    parser = argparse.ArgumentParser(
        description="vCenter/ESX/ESXi remote inventory from command line (Standalone Python Edition)"
    )
    parser.add_argument("--host", help="ESX server hostname")
    parser.add_argument("--user", help="User name")
    parser.add_argument("--password", help="User password")
    parser.add_argument("--path", help="Output directory or file", default="-")
    parser.add_argument("--json", action="store_true", help="Use JSON format")
    parser.add_argument("--dump", action="store_true", help="Also dump host info")
    parser.add_argument("--dumpfile", help="Generate inventory from dump file")
    parser.add_argument("--debug", action="count", default=0, help="Enable debug logging")
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    args = parser.parse_args()

    if args.version:
        print_version()
        sys.exit(0)

    config = Config(vars(args))
    logger = Logger(config)
    temp_dir = tempfile.mkdtemp()

    try:
        target = LocalTarget(logger=logger, path=args.path, json_format=args.json, basevardir=temp_dir)
        esx = ESX(logger=logger, config=config, target=target)

        if args.dumpfile:
            inventory_from_dump(esx, args)

        if not all([args.host, args.user, args.password]):
            parser.print_help()
            sys.exit(1)

        if not esx.connect(args.host, args.user, args.password):
            print(f"Connection failed: {esx.last_error()}", file=sys.stderr)
            sys.exit(1)

        dump_callback = dump_from_hostfullinfo if args.dump else None
        esx.server_inventory(args.path, dump_callback)
        sys.exit(0)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()