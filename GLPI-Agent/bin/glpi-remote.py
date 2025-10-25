#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
glpi_remote.py — A Python equivalent of glpi-remote Perl tool.
"""

import os
import sys
import json
import time
import gzip
import zlib
import uuid
import base64
import hashlib
import argparse
import requests
import tempfile
from datetime import datetime
from xml.etree import ElementTree as ET


VERSION = "1.0"

# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def generate_id():
    """Generate short request id based on time."""
    digest = hashlib.sha1(f"{time.time()}{uuid.uuid4()}".encode()).hexdigest()
    return digest[:8]


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def decompress(content, content_type):
    """Handle zlib/gzip decompression."""
    if content_type == "application/x-compress-zlib":
        return zlib.decompress(content)
    elif content_type == "application/x-compress-gzip":
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp.flush()
            with gzip.open(tmp.name, "rb") as gz:
                return gz.read()
    return content


def safe_print(msg):
    sys.stdout.write(str(msg) + "\n")
    sys.stdout.flush()

# ---------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------

def cmd_help(args):
    safe_print("Usage: glpi_remote.py [command] [options]\nAvailable commands: list, add, delete, agent")
    sys.exit(0)


def cmd_list(args):
    vardir = args.vardir or "./vardir"
    targets_dir = os.path.join(vardir, "targets")

    if not os.path.exists(targets_dir):
        safe_print("No targets found.")
        return

    for root, dirs, files in os.walk(targets_dir):
        for file in files:
            if file.endswith(".json"):
                target = load_json(os.path.join(root, file))
                safe_print(f"{target.get('id', '?'):10s} {target.get('type', '?'):8s} {target.get('url', '')}")


def cmd_add(args):
    vardir = args.vardir or "./vardir"
    targets_dir = os.path.join(vardir, "targets")
    os.makedirs(targets_dir, exist_ok=True)

    for url in args.urls:
        data = {
            "id": generate_id(),
            "url": url,
            "type": "remote",
            "added": datetime.now().isoformat()
        }
        save_json(os.path.join(targets_dir, f"{data['id']}.json"), data)
        safe_print(f"Added remote target: {url}")


def cmd_delete(args):
    vardir = args.vardir or "./vardir"
    targets_dir = os.path.join(vardir, "targets")

    if not args.ids:
        safe_print("Error: No IDs provided.")
        return

    for _id in args.ids:
        path = os.path.join(targets_dir, f"{_id}.json")
        if os.path.exists(path):
            os.remove(path)
            safe_print(f"Deleted target {_id}")
        else:
            safe_print(f"No target with ID {_id}")


def cmd_agent(args):
    if not args.token:
        safe_print("Error: Missing token (--token)")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"User-Agent": f"GLPI-Remote/{VERSION}"})
    timeout = args.timeout or 10
    request_id = args.id or generate_id()

    for host in args.hosts:
        scheme = "https" if args.ssl else "http"
        baseurl = args.baseurl or "/inventory"
        url = f"{scheme}://{host}:{args.port or 62354}{baseurl}"

        safe_print(f"Connecting to {url} ...")
        r = session.get(f"{url}/session", timeout=timeout, verify=not args.no_ssl_check)

        if not r.ok:
            safe_print(f"{host}: No session ({r.status_code})")
            continue

        nonce = r.headers.get("X-Auth-Nonce")
        if not nonce:
            safe_print("No nonce returned.")
            continue

        sha = hashlib.sha256(f"{nonce}++{args.token}".encode()).digest()
        payload = base64.b64encode(sha).decode()

        headers = {
            "X-Auth-Payload": payload,
            "X-Request-ID": request_id,
            "Accept": "application/xml, application/x-compress-zlib, application/x-compress-gzip"
        }

        resp = session.get(f"{url}/get", headers=headers, timeout=timeout, verify=not args.no_ssl_check)

        if not resp.ok:
            safe_print(f"{host}: Inventory request failed ({resp.status_code})")
            continue

        content = decompress(resp.content, resp.headers.get("Content-Type", ""))
        try:
            xml_root = ET.fromstring(content)
            deviceid = xml_root.findtext(".//DEVICEID") or "unknown"
        except Exception:
            safe_print(f"{host}: Invalid XML, skipping.")
            continue

        safe_print(f"{host}: Got inventory for {deviceid}")

        if args.directory:
            os.makedirs(args.directory, exist_ok=True)
            filename = os.path.join(args.directory, f"{deviceid}.xml")
            with open(filename, "wb") as f:
                f.write(content)
            safe_print(f"Written inventory to {filename}")
        else:
            safe_print(content.decode() if isinstance(content, bytes) else content)


# ---------------------------------------------------------------------
# Main parser and dispatcher
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GLPI Remote Python equivalent")
    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list")
    p_list.add_argument("--vardir", help="Storage directory")
    p_list.set_defaults(func=cmd_list)

    # add
    p_add = subparsers.add_parser("add")
    p_add.add_argument("urls", nargs="+", help="List of remote URLs to add")
    p_add.add_argument("--vardir", help="Storage directory")
    p_add.set_defaults(func=cmd_add)

    # delete
    p_del = subparsers.add_parser("delete")
    p_del.add_argument("ids", nargs="+", help="IDs to delete")
    p_del.add_argument("--vardir", help="Storage directory")
    p_del.set_defaults(func=cmd_delete)

    # agent
    p_agent = subparsers.add_parser("agent")
    p_agent.add_argument("hosts", nargs="+", help="Remote hostnames")
    p_agent.add_argument("--token", "-K", required=True, help="Shared secret token")
    p_agent.add_argument("--directory", "-d", help="Output directory for XMLs")
    p_agent.add_argument("--port", "-p", type=int, help="Port number")
    p_agent.add_argument("--timeout", "-t", type=int, help="Timeout in seconds")
    p_agent.add_argument("--ssl", action="store_true", help="Use SSL (https)")
    p_agent.add_argument("--no-ssl-check", action="store_true", help="Disable SSL cert verification")
    p_agent.add_argument("--baseurl", "-b", help="Base URL path")
    p_agent.add_argument("--id", "-I", help="Request ID")
    p_agent.set_defaults(func=cmd_agent)

    # help
    p_help = subparsers.add_parser("help")
    p_help.set_defaults(func=cmd_help)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()