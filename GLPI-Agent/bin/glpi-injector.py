#!/usr/bin/env python3
"""
glpi-injector - Standalone tool to push inventory files (XML/JSON)
to GLPI, OCS Inventory, or compatible servers.

Fully functional Python 3 implementation — no GLPI Agent dependencies required.
Supports gzip compression, OAuth2 token auth, SSL options, and proxy settings.
"""

import sys
import os
import argparse
import json
import gzip
import uuid
import re
import time
import random
import requests
import platform
from urllib.parse import urlparse, urlunparse
import xml.etree.ElementTree as ET

# Try safe file locking (fcntl for UNIX, skip on Windows)
try:
    import fcntl
    USE_FCNTL = True
except ImportError:
    USE_FCNTL = False

failed_files = []

# ---------------------------------------------------------------------
# XML Parsing Helpers
# ---------------------------------------------------------------------
def element_to_dict(element):
    """Recursively convert XML ElementTree to a Python dict."""
    d = {}
    if element.attrib:
        d['@attrib'] = dict(element.attrib)
    if element.text and element.text.strip():
        d['#text'] = element.text.strip()

    children = {}
    for child in element:
        child_dict = element_to_dict(child)
        tag = child.tag
        if tag in children:
            if not isinstance(children[tag], list):
                children[tag] = [children[tag]]
            children[tag].append(child_dict)
        else:
            children[tag] = child_dict

    if children:
        d[element.tag] = children
    elif '#text' in d:
        d[element.tag] = d['#text']
        del d['#text']
    else:
        d[element.tag] = None

    return d


def xml_to_dict(xml_string):
    """Convert XML string to dict."""
    try:
        root = ET.fromstring(xml_string)
        return element_to_dict(root)
    except Exception:
        return None


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def uncompress(data):
    """Decompress gzip data if possible, otherwise return raw bytes."""
    try:
        return gzip.decompress(data)
    except Exception:
        return data


def new_agentid():
    """Generate a new random UUID."""
    return str(uuid.uuid4()).lower()


# ---------------------------------------------------------------------
# Core Send Function
# ---------------------------------------------------------------------
def send_content(content_bytes, agentid, args):
    """Send one inventory file or data blob to the GLPI/OCS endpoint."""
    content = uncompress(content_bytes)
    useragent = args.useragent or 'GLPI-Injector'
    verify = not args.no_ssl_check
    cert = args.ssl_cert_file if args.ssl_cert_file else None

    # Extract client version from XML or JSON to set User-Agent if requested
    if args.xml_ua or args.json_ua:
        if content.startswith(b'<?xml'):
            tree = xml_to_dict(content)
            if tree and 'REQUEST' in tree and 'CONTENT' in tree['REQUEST']:
                ver = tree['REQUEST']['CONTENT'].get('VERSIONCLIENT')
                if ver:
                    useragent = ver
        elif b'{' in content:
            try:
                j = json.loads(content.decode('utf-8'))
                ver = j.get('content', {}).get('versionclient')
                if ver:
                    useragent = ver
            except Exception:
                pass

    # Create session
    session = requests.Session()
    session.headers.update({'User-Agent': useragent})

    if args.proxy:
        session.proxies = {'http': args.proxy, 'https': args.proxy}

    url = args.url
    info = ""

    if args.no_ssl_check and url.startswith('https'):
        info = " (SSL check disabled)"

    # OAuth2 Client Credentials flow
    bearer_token = None
    if args.oauth_client_id and args.oauth_client_secret:
        parsed = urlparse(url)
        path = parsed.path
        match = re.match(r'^(.*)(marketplace|plugins).*', path)
        if match:
            path = match.group(1)
        path = path.rstrip('/') + '/api.php/token'
        token_url = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))

        oauth_data = {
            'grant_type': 'client_credentials',
            'client_id': args.oauth_client_id,
            'client_secret': args.oauth_client_secret,
            'scope': 'inventory'
        }

        try:
            resp_oauth = session.post(token_url, json=oauth_data, verify=verify, cert=cert)
            if resp_oauth.ok:
                bearer_token = resp_oauth.json().get('access_token')
            else:
                print(f"ERROR (OAuth): {resp_oauth.status_code} {resp_oauth.reason}")
        except Exception as e:
            print(f"ERROR (OAuth): {e}")

    headers = {
        'Pragma': 'no-cache',
    }

    if args.no_compression:
        headers['Content-Type'] = 'application/json' if agentid else 'application/xml'
        content_to_send = content
    else:
        headers['Content-Type'] = 'application/x-compress-zlib'
        content_to_send = gzip.compress(content)

    if agentid:
        headers['GLPI-Agent-ID'] = agentid
    if bearer_token:
        headers['Authorization'] = f"Bearer {bearer_token}"

    # Debug request ID
    requestid = None
    if args.debug:
        requestid = ''.join(random.choice('0123456789ABCDEF') for _ in range(8))
        headers['GLPI-Request-ID'] = requestid
        print(f"[DEBUG] Sending request {requestid} (AgentID={agentid})")

    try:
        resp = session.post(url, data=content_to_send, headers=headers, verify=verify, cert=cert, allow_redirects=True)
    except requests.RequestException as e:
        print(f"ERROR: Request failed ({e})")
        return False

    # Handle response
    error = None
    content_resp = resp.content
    if 'x-compress-zlib' in resp.headers.get('Content-Type', ''):
        if args.debug:
            print("DEBUG: decompressing response content")
        content_resp = uncompress(content_resp)

    # Parse response (XML or JSON)
    try:
        if content_resp.startswith(b'<?xml'):
            tree = xml_to_dict(content_resp)
            if not tree:
                raise ValueError("Invalid XML response")
            reply = tree.get('REPLY', {})
            if isinstance(reply, dict) and 'ERROR' in reply:
                error = reply['ERROR']
        elif content_resp.startswith(b'{'):
            j = json.loads(content_resp.decode('utf-8'))
            if j.get('status') == 'error':
                error = j.get('message', 'Server import error')
        else:
            error = f"Unrecognized response format ({content_resp[:50]})"
    except Exception as e:
        error = f"Response parsing failed: {e}"

    if args.verbose or args.debug:
        if error:
            print(f"ERROR{info}: {resp.status_code} {resp.reason}, {error}")
        else:
            print(f"OK: {resp.status_code} {resp.reason}")

    return resp.ok and not error


# ---------------------------------------------------------------------
# File and Directory Handling
# ---------------------------------------------------------------------
def load_file(file_path, args):
    """Load and send a single file."""
    if not os.path.isfile(file_path):
        sys.exit(f"File {file_path} not found.")
    if not os.access(file_path, os.R_OK):
        sys.exit(f"File {file_path} not readable.")

    if args.verbose:
        print(f"Processing file: {file_path}")

    with open(file_path, 'rb') as f:
        if USE_FCNTL:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(f"File {file_path} is locked, skipping.")
                return
        content = f.read()

    uuid_match = re.search(r'([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\.(?:json|data)$', file_path, re.I)
    agentid = uuid_match.group(1) if uuid_match else new_agentid()

    success = send_content(content, agentid, args)
    if success and args.remove:
        try:
            os.unlink(file_path)
            if args.verbose:
                print(f"Removed {file_path}")
        except OSError as e:
            print(f"Failed to remove {file_path}: {e}")

    if not success:
        failed_files.append(file_path)


def load_directory(directory, args):
    """Process all inventory files in a directory."""
    if not os.path.isdir(directory):
        sys.exit(f"Directory {directory} not found.")

    for root, _, files in os.walk(directory):
        for file in files:
            if re.search(r'\.(?:data|json|ocs|xml)$', file):
                load_file(os.path.join(root, file), args)
        if not args.recursive:
            break


def load_stdin(args):
    """Read and send inventory data from STDIN."""
    content = sys.stdin.buffer.read()
    agentid = new_agentid() if b'{' in content else None
    success = send_content(content, agentid, args)
    if not success:
        failed_files.append('STDIN')


# ---------------------------------------------------------------------
# CLI Main
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Push GLPI/OCS inventory data to a server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  glpi-injector -v -f /tmp/toto.json --url https://example.com/
  glpi-injector -v -R -d /srv/ftp/fusion --url https://example.com/
"""
    )
    parser.add_argument('-d', '--directory', help='load every inventory file from directory')
    parser.add_argument('-R', '--recursive', action='store_true', help='recursively load inventory files')
    parser.add_argument('-f', '--file', help='load a specific file')
    parser.add_argument('-u', '--url', required=True, help='server URL')
    parser.add_argument('-r', '--remove', action='store_true', help='remove successfully injected files')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    parser.add_argument('--debug', action='store_true', help='debug mode')
    parser.add_argument('--stdin', action='store_true', help='read data from STDIN')
    parser.add_argument('--useragent', help='custom HTTP User-Agent for POST')
    parser.add_argument('-x', '--xml-ua', action='store_true', help='extract UA from XML')
    parser.add_argument('--json-ua', action='store_true', help='extract UA from JSON')
    parser.add_argument('-C', '--no-compression', action='store_true', help='disable compression')
    parser.add_argument('-P', '--proxy', help='use proxy (http://proxy:port)')
    parser.add_argument('--no-ssl-check', action='store_true', help='disable SSL check')
    parser.add_argument('--ssl-cert-file', help='client certificate file')
    parser.add_argument('--oauth-client-id', help='OAuth client ID')
    parser.add_argument('--oauth-client-secret', help='OAuth client secret')

    args = parser.parse_args()
    if args.debug:
        args.verbose = True

    if args.stdin:
        load_stdin(args)
    elif args.file:
        load_file(args.file, args)
    elif args.directory:
        load_directory(args.directory, args)
    else:
        parser.print_help()
        sys.exit(1)

    if failed_files:
        print("\nFailed to send:")
        for f in failed_files:
            print(f" - {f}")
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()