#!/usr/bin/env python3
"""
GLPI Agent License Tools - Python Implementation

This module provides license-related functions for Adobe and Microsoft products.
"""

from typing import Dict, List, Optional, Tuple
import re

# Import the main Tools module functions
try:
    from GLPI.Agent.Tools import get_all_lines, all_func
except ImportError:
    import sys
    sys.path.insert(0, '../../')
    from Tools import get_all_lines, all_func


__all__ = [
    'get_adobe_licenses',
    'get_adobe_licenses_without_sqlite',
    'decode_microsoft_key'
]


def _decode_adobe_key(encrypted_key: Optional[str]) -> Optional[str]:
    """
    Decode Adobe encrypted key.
    
    Thanks to Brandon Mulcahy - http://www.a1vbcode.com/snippet-4796.asp
    
    Args:
        encrypted_key: Encrypted key string
        
    Returns:
        Decoded key in format XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    """
    if not encrypted_key:
        return None
    
    cipher_key = [
        '0000000001', '5038647192', '1456053789', '2604371895',
        '4753896210', '8145962073', '0319728564', '7901235846',
        '7901235846', '0319728564', '8145962073', '4753896210',
        '2604371895', '1426053789', '5038647192', '3267408951',
        '5038647192', '2604371895', '8145962073', '7901235846',
        '3267408951', '1426053789', '4753896210', '0319728564'
    ]
    
    decrypted_key_chars = []
    cipher_idx = 0
    
    for char in encrypted_key:
        if cipher_idx >= len(cipher_key):
            break
        sub_cipher_key = cipher_key[cipher_idx]
        cipher_idx += 1
        
        try:
            char_idx = int(char)
            if 0 <= char_idx < len(sub_cipher_key):
                decrypted_key_chars.append(sub_cipher_key[char_idx])
        except (ValueError, IndexError):
            continue
    
    if len(decrypted_key_chars) < 24:
        return None
    
    # Format as XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    return '-'.join([
        ''.join(decrypted_key_chars[i:i+4])
        for i in range(0, 24, 4)
    ])


def get_adobe_licenses(**params) -> List[Dict[str, str]]:
    """
    Get Adobe licenses from database query output.
    
    Args:
        **params: Parameters for get_all_lines (command, file, etc.)
        
    Returns:
        List of license dictionaries with NAME, FULLNAME, KEY, COMPONENTS
    """
    lines = get_all_lines(**params)
    if not lines:
        return []
    
    licenses = []
    data = {}
    
    for line in lines:
        fields = line.split(' <> ')
        
        if len(fields) < 4:
            continue
        
        # Clean up fields
        fields[1] = re.sub(r'\{\|\}.*', '', fields[1])
        fields[2] = re.sub(r'\{\|\}.*', '', fields[2])
        fields[3] = re.sub(r'\{\|\}.*', '', fields[3])
        
        if fields[2] == 'FLMap':
            # Component mapping
            if fields[3] not in data:
                data[fields[3]] = {}
            if 'with' not in data[fields[3]]:
                data[fields[3]]['with'] = []
            data[fields[3]]['with'].append(fields[1])
        elif fields[3] != "unlicensed":
            # License data
            if fields[1] not in data:
                data[fields[1]] = {}
            data[fields[1]][fields[2]] = fields[3]
    
    for key in sorted(data.keys()):
        if 'SN' not in data[key] and 'with' not in data[key]:
            continue
        
        decoded_key = _decode_adobe_key(data[key].get('SN')) if 'SN' in data[key] else None
        
        licenses.append({
            'NAME': key,
            'FULLNAME': data[key].get('ALM_LicInfo_EpicAppName', ''),
            'KEY': decoded_key or 'n/a',
            'COMPONENTS': '/'.join(sorted(data[key].get('with', [])))
        })
    
    return licenses


def get_adobe_licenses_without_sqlite(file_adobe: str) -> List[Dict[str, str]]:
    """
    Get Adobe licenses from file without using SQLite.
    
    Args:
        file_adobe: Path to Adobe license file
        
    Returns:
        List of license dictionaries with NAME, FULLNAME, KEY, COMPONENTS
    """
    content = get_all_lines(file=file_adobe)
    if not content:
        return []
    
    # Join lines into single string and remove null bytes
    content_str = '\n'.join(content) if isinstance(content, list) else content
    content_str = content_str.replace('\x00', '')
    
    licenses = []
    products = {}
    copy_content = content_str
    
    # Extract product to component mappings
    pattern = r'1([a-zA-Z0-9\-.]+)[\{\|\}[a-zA-Z0-9\-_]*]?FLMap([a-zA-Z0-9\-.]{3,}).{2,3}'
    matches = re.findall(pattern, copy_content)
    
    for component, product in matches:
        if product in products:
            if component not in products[product]:
                products[product].append(component)
        else:
            products[product] = [component]
    
    for product in sorted(products.keys()):
        component = products[product]
        
        # Extract serial number for this product
        regex = re.escape(product) + r'\{\|\}[a-zA-Z0-9\-_]+SN([0-9]{24})'
        match = re.search(regex, content_str)
        
        if match:
            sn = _decode_adobe_key(match.group(1))
            
            # Extract full name for this product
            regex = re.escape(product) + r'ALM_LicInfo_EpicAppName\{\|\}[0-9]+([a-zA-Z]+[a-zA-Z0-9\.\- ]+).{2}'
            match = re.search(regex, content_str)
            full_name = match.group(1) if match else product
            
            licenses.append({
                'NAME': product,
                'FULLNAME': full_name,
                'KEY': sn or 'n/a',
                'COMPONENTS': '/'.join(sorted(component))
            })
    
    return licenses


def decode_microsoft_key(raw: bytes) -> Optional[str]:
    """
    Decode Microsoft product key from binary data.
    
    Inspired by http://poshcode.org/4363
    
    Args:
        raw: Raw binary data containing the key
        
    Returns:
        Decoded product key in format XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
    """
    if not raw:
        return None
    
    # Convert to list of bytes
    if isinstance(raw, str):
        key_bytes = [ord(c) for c in raw]
    else:
        key_bytes = list(raw)
    
    # Select correct bytes range:
    # - 808 to 822 for new style keys (Office 2010 and later)
    # - 52 to 66 for old style keys
    first_byte = 808 if len(key_bytes) > 808 and key_bytes[808] != 0 else 52
    last_byte = first_byte + 14
    
    if last_byte >= len(key_bytes):
        return None
    
    # Check for Windows 8/Office 2013 style key (can contain the letter "N")
    contains_n = (key_bytes[last_byte] >> 3) & 1
    key_bytes[last_byte] = key_bytes[last_byte] & 0xF7
    
    # Product key available characters
    letters = ['B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'M', 'P', 'Q', 'R', 
               'T', 'V', 'W', 'X', 'Y', '2', '3', '4', '6', '7', '8', '9']
    
    # Extract relevant bytes
    bytes_slice = key_bytes[first_byte:last_byte + 1]
    
    # Return None for null keys
    if all(b == 0 for b in bytes_slice):
        return None
    
    # Decode product key
    chars = [''] * 25
    
    for i in range(24, -1, -1):
        index = 0
        for j in range(14, -1, -1):
            value = (index << 8) | bytes_slice[j]
            bytes_slice[j] = value // len(letters)
            index = value % len(letters)
        chars[i] = letters[index]
    
    # Handle Windows 8/Office 2013 style keys with 'N'
    if contains_n != 0:
        first_char = chars.pop(0)
        first_char_index = letters.index(first_char) if first_char in letters else 0
        chars.insert(first_char_index, 'N')
    
    # Format as XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
    return '-'.join([
        ''.join(chars[i:i+5])
        for i in range(0, 25, 5)
    ])


if __name__ == '__main__':
    print("GLPI Agent License Tools")
    print("Available functions:")
    for func in __all__:
        print(f"  - {func}")
    
    # Test Adobe key decoding
    print("\nTesting Adobe key decoding:")
    test_key = "123456789012345678901234"
    print(f"  _decode_adobe_key('{test_key}'): {_decode_adobe_key(test_key)}")
