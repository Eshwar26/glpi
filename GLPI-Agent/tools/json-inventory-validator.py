#!/usr/bin/env python3
"""
JSON Inventory Validator - Python Implementation

Validates JSON files against GLPI inventory schema or a given schema file.
Converted from the original Perl implementation.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import jsonschema
    from jsonschema import Draft7Validator, validators
except ImportError:
    print("ERROR: jsonschema module required", file=sys.stderr)
    print("Install it with: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERROR: requests module required for loading remote schemas", file=sys.stderr)
    print("Install it with: pip install requests", file=sys.stderr)
    sys.exit(1)


INVENTORY_SCHEMA_URL = "https://raw.githubusercontent.com/glpi-project/inventory_format/master/inventory.schema.json"


def load_schema(schema_path: str) -> Dict[str, Any]:
    """
    Load JSON schema from URL or file.
    
    Args:
        schema_path: URL or file path to schema
    
    Returns:
        Schema dictionary
    """
    if schema_path.startswith('http://') or schema_path.startswith('https://'):
        # Load from URL
        response = requests.get(schema_path)
        response.raise_for_status()
        return response.json()
    else:
        # Load from file
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def validate_json_file(file_path: str, validator: Draft7Validator) -> bool:
    """
    Validate a JSON file against the schema.
    
    Args:
        file_path: Path to JSON file
        validator: JSON schema validator
    
    Returns:
        True if valid, False if errors found
    """
    print(f"Validating {file_path}... ", end='', flush=True)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON")
        print(f"     {e}")
        return False
    except FileNotFoundError:
        print(f"ERROR: File not found")
        return False
    
    # Validate against schema
    errors = list(validator.iter_errors(data))
    
    if errors:
        print("ERROR:")
        for idx, error in enumerate(errors, 1):
            # Get the path to the error
            path = "/" + "/".join(str(p) for p in error.absolute_path)
            
            # Try to get the value at that path
            value = data
            try:
                for key in error.absolute_path:
                    if isinstance(value, dict):
                        value = value[key]
                    elif isinstance(value, list) and isinstance(key, int):
                        value = value[key]
                    else:
                        value = None
                        break
            except (KeyError, IndexError, TypeError):
                value = None
            
            # Format value
            if isinstance(value, (dict, list)):
                import pprint
                value_str = pprint.pformat(value, width=70, compact=True)
                # Indent subsequent lines
                value_str = "\n     ".join(value_str.split('\n'))
            elif value is not None:
                value_str = str(value)
                # Quote strings in error messages that mention string type
                if 'string' in error.message.lower():
                    value_str = f"'{value_str}'"
            else:
                value_str = None
            
            # Print error
            print(f"{idx:3d}: {path}", end='')
            if value_str:
                print(f" => {value_str}")
            else:
                print()
            print(f"     {error.message}")
        
        return False
    else:
        print("OK")
        return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Validate JSON files against GLPI inventory schema or given schema file',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--schema',
        help='Use given file as JSON schema',
        metavar='FILE'
    )
    parser.add_argument(
        'json_files',
        nargs='*',
        help='JSON files to validate',
        metavar='JSON_FILES'
    )
    
    args = parser.parse_args()
    
    # Determine schema to use
    if args.schema:
        schema_path = args.schema
        if Path(schema_path).exists():
            print(f"Loading schema from {schema_path} file...")
            schema_path = str(Path(schema_path).absolute())
        else:
            print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
            return 1
    else:
        schema_path = INVENTORY_SCHEMA_URL
        print("Loading inventory schema from url...")
        print(schema_path)
    
    # Load and validate schema
    try:
        schema = load_schema(schema_path)
    except Exception as e:
        print(f"ERROR: Failed to load schema: {e}", file=sys.stderr)
        return 1
    
    # Create validator
    try:
        # Check if schema is valid
        Draft7Validator.check_schema(schema)
        validator = Draft7Validator(schema)
    except jsonschema.SchemaError as e:
        print(f"ERROR: Invalid schema: {e}", file=sys.stderr)
        return 1
    
    print("Inventory schema loaded")
    print("---")
    
    # Validate each file
    if not args.json_files:
        print("No JSON files provided to validate", file=sys.stderr)
        return 0
    
    has_errors = False
    for file_path in args.json_files:
        if not Path(file_path).exists():
            print(f"Skipping non-existent file: {file_path}")
            continue
        
        if not validate_json_file(file_path, validator):
            has_errors = True
    
    return 1 if has_errors else 0


if __name__ == '__main__':
    sys.exit(main())

