#!/usr/bin/env python3

"""
Perl BEGIN/END logging redirection equivalent.

This Python code mimics the Perl BEGIN and END blocks for redirecting
STDOUT and STDERR to log files if the logs directory exists.
"""

import sys
import os
import atexit
from datetime import datetime

# Mimic BEGIN block: executed at module/script start
logdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../logs'))

if os.path.isdir(logdir):
    try:
        stderr_file = open(os.path.join(logdir, 'stderr.txt'), 'w')
        stdout_file = open(os.path.join(logdir, 'stdout.txt'), 'w')
        
        # Redirect stderr and stdout
        sys.stderr = os.fdopen(stderr_file.fileno(), 'w', buffering=1)
        sys.stdout = os.fdopen(stdout_file.fileno(), 'w', buffering=1)
        
        # Print BEGIN messages
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ": BEGIN stderr.txt", file=sys.stderr)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ": BEGIN stdout.txt")
        
    except IOError as io_error:
        # Fallback to original stderr if redirection fails
        orig_stderr = sys.__stderr__
        print(f"Can't redirect STDERR to stderr.txt: {io_error}", file=orig_stderr)
        sys.exit(1)
else:
    # Use original stderr
    orig_stderr = sys.__stderr__
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f": Logging folder {logdir} is missing", file=orig_stderr)

# Mimic END block: executed on exit
def end_logging():
    try:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ": END stderr.txt", file=sys.stderr)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ": END stdout.txt")
    except:
        # If streams are closed or error, ignore
        pass

atexit.register(end_logging)

# Rest of the script would go here...
# For demonstration, print a message
print("This is a test message after redirection.")