#!/usr/bin/env python3
"""
glpi-netinventory - Standalone Network Inventory
A pure Python implementation of the GLPI NetInventory task.
"""

import sys
import os
import argparse
import time
import socket
import json
import platform
import concurrent.futures
import logging

# ==============================================================
# Version & Metadata
# ==============================================================

NETINVENTORY_VERSION = "2.0.0"
VERSION = "2.0.0"
PROVIDER = "PythonNetInventory"
COMMENTS = ["Standalone version, rewritten in pure Python."]

# ==============================================================
# Core Classes
# ==============================================================

class Config:
    """Configuration container"""
    def __init__(self, options=None):
        self.options = options or {}
        for k, v in self.options.items():
            setattr(self, k.replace('-', '_'), v)


class Logger:
    """Simple logger with debug and info levels"""
    def __init__(self, config=None):
        debug_level = (config or {}).get("debug", 0)
        logging.basicConfig(
            level=logging.DEBUG if debug_level else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.logger = logging.getLogger("netinventory")

    def debug(self, msg): self.logger.debug(msg)
    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)


class LocalTarget:
    """Represents local output storage for inventories"""
    def __init__(self, path=None, basevardir=None):
        self.path = path or "./output"
        self.basevardir = basevardir or "./var"
        os.makedirs(self.basevardir, exist_ok=True)
        os.makedirs(self.path, exist_ok=True)

    def save_result(self, data, filename="inventory.json"):
        file_path = os.path.join(self.path, filename)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return file_path


# ==============================================================
# NetInventory Job
# ==============================================================

class NetInventoryJob:
    """Handles scanning and data collection for multiple devices"""

    def __init__(self, logger=None, params=None, devices=None,
                 credentials=None, showcontrol=None):
        self.logger = logger or Logger()
        self.params = params or {}
        self.devices = devices or []
        self.credentials = credentials or []
        self.showcontrol = showcontrol

    def _simulate_snmp_query(self, device):
        """Simulate SNMP data collection"""
        ip = device.get("IP") or "unknown"
        port = device.get("PORT", 161)
        version = self.credentials[0].get("VERSION", "2c")
        community = self.credentials[0].get("COMMUNITY", "public")

        self.logger.debug(f"Querying {ip}:{port} via SNMPv{version} ({community})")
        time.sleep(0.2)

        try:
            socket.gethostbyname(ip)
            reachable = True
        except socket.error:
            reachable = False

        if not reachable:
            self.logger.error(f"Device {ip} is unreachable.")
            return None

        # Simulated SNMP data
        result = {
            "ip": ip,
            "port": port,
            "hostname": f"device-{ip.replace('.', '-')}",
            "snmp_version": version,
            "community": community,
            "uptime": f"{int(time.time()) % 86400}s",
            "description": f"Simulated network device ({ip})",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return result

    def run(self):
        """Run the job using multiple threads"""
        if not self.devices:
            self.logger.error("No devices to inventory.")
            return

        threads = int(self.params.get("THREADS_QUERY", 1))
        self.logger.info(f"Running inventory on {len(self.devices)} devices using {threads} thread(s).")

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            for result in executor.map(self._simulate_snmp_query, self.devices):
                if result:
                    results.append(result)

        print("\n===== Inventory Results =====")
        print(json.dumps(results, indent=2))
        print("=============================\n")

        return results


# ==============================================================
# Main NetInventory Controller
# ==============================================================

class NetInventory:
    """Controls one or more inventory jobs"""
    def __init__(self, target=None, config=None, logger=None, **kwargs):
        self.target = target
        self.config = config or Config()
        self.logger = logger or Logger()
        self.jobs = []
        for k, v in kwargs.items():
            setattr(self, k, v)

    def run(self):
        """Run all jobs sequentially"""
        if not self.jobs:
            self.logger.error("No jobs configured.")
            return

        self.logger.info(f"Starting NetInventory ({NETINVENTORY_VERSION})")
        all_results = []
        for job in self.jobs:
            job_results = job.run()
            if job_results:
                all_results.extend(job_results)

        if self.target:
            file_path = self.target.save_result(all_results)
            self.logger.info(f"Inventory saved to: {file_path}")
        else:
            self.logger.info("No output target specified.")
        self.logger.info("Inventory task completed successfully.")


# ==============================================================
# Utility Functions
# ==============================================================

def parse_credentials(cred_str):
    cred = {"ID": 1}
    if not cred_str:
        return cred
    for param in cred_str.split(","):
        if ":" in param:
            k, v = param.split(":", 1)
            cred[k.upper()] = v
    return cred


def print_version():
    print(f"NetInventory v{NETINVENTORY_VERSION} ({PROVIDER})")
    for c in COMMENTS:
        print(c)


def print_help():
    print("""Usage: glpi-netinventory [options]

Options:
  --host <HOST>            Target device IP or hostname
  --file <FILE>            Load from saved SNMP data file
  --community <STRING>     SNMP community (default: public)
  --credentials <STRING>   SNMP credentials (e.g., version:2c,community:public)
  --threads <COUNT>        Number of threads (default: 1)
  --timeout <SECONDS>      Timeout per query (default: 15)
  --debug                  Enable debug logging
  --control                Show control messages
  --help, -h               Show this help
  --version                Show version info

Examples:
  glpi-netinventory --host 192.168.1.10
  glpi-netinventory --host 10.0.0.5 --community private
""")


# ==============================================================
# Main Function
# ==============================================================

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host", action="append")
    parser.add_argument("--file", action="append")
    parser.add_argument("--community")
    parser.add_argument("--credentials")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--debug", action="count", default=0)
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", action="store_true")

    args = parser.parse_args()

    if args.help:
        print_help()
        return 0
    if args.version:
        print_version()
        return 0

    if not args.host and not args.file:
        print_help()
        print("\nError: No host or file provided.\n", file=sys.stderr)
        return 1

    # Initialize logging and config
    options = {"debug": args.debug, "threads": args.threads, "timeout": args.timeout}
    logger = Logger(config=options)
    target = LocalTarget(path="./inventory_results", basevardir="./var")

    # Build credentials
    if args.credentials:
        creds = [parse_credentials(args.credentials)]
    else:
        creds = [{"ID": 1, "VERSION": "2c", "COMMUNITY": args.community or "public"}]

    # Build devices
    devices = []
    if args.file:
        for idx, f in enumerate(args.file, 1):
            devices.append({"ID": idx, "FILE": f, "IP": "127.0.0.1"})
    if args.host:
        for idx, h in enumerate(args.host, 1):
            devices.append({"ID": idx, "IP": h})

    if not devices:
        logger.error("No devices found to inventory.")
        return 1

    # Create and run inventory
    inventory = NetInventory(target=target, config=Config(options), logger=logger)
    inventory.jobs = [
        NetInventoryJob(
            logger=logger,
            params={"THREADS_QUERY": args.threads, "TIMEOUT": args.timeout},
            devices=devices,
            credentials=creds,
            showcontrol=args.control
        )
    ]

    inventory.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())