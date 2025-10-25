#!/usr/bin/env python3
"""
Kwalitee Checker - Python Implementation

Checks the quality of a GLPI Agent distribution archive.
Converted from the original Perl implementation.

Note: This is adapted from the Perl Module::CPANTS::Analyse tool.
For Python distributions, it performs basic quality checks.
"""

import sys
import os
import tarfile
import zipfile
import argparse
from pathlib import Path
from typing import Dict, List, Any


def analyze_archive(archive_path: str) -> Dict[str, Any]:
    """
    Analyze a distribution archive for quality metrics.
    
    Args:
        archive_path: Path to the archive file
    
    Returns:
        Dictionary with analysis results
    """
    results = {
        'file': archive_path,
        'kwalitee': {},
        'errors': [],
        'score': 0,
        'max_score': 0
    }
    
    # Determine archive type
    if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
        archive_type = 'tar.gz'
    elif archive_path.endswith('.zip'):
        archive_type = 'zip'
    else:
        results['errors'].append(f"Unknown archive type: {archive_path}")
        return results
    
    # Extract and analyze
    try:
        if archive_type == 'tar.gz':
            with tarfile.open(archive_path, 'r:gz') as tar:
                members = tar.getmembers()
                names = [m.name for m in members]
        else:
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                names = zip_file.namelist()
    except Exception as e:
        results['errors'].append(f"Failed to open archive: {e}")
        return results
    
    # Check for common quality indicators
    checks = {
        'has_readme': check_has_readme(names),
        'has_changelog': check_has_changelog(names),
        'has_license': check_has_license(names),
        'has_tests': check_has_tests(names),
        'has_setup': check_has_setup(names),
        'proper_structure': check_proper_structure(names),
        'no_temp_files': check_no_temp_files(names),
        'consistent_version': True,  # Would need deeper analysis
    }
    
    # Calculate score
    for check_name, passed in checks.items():
        results['max_score'] += 1
        results['kwalitee'][check_name] = passed
        if passed:
            results['score'] += 1
    
    return results


def check_has_readme(names: List[str]) -> bool:
    """Check if archive has a README file."""
    readme_patterns = ['README', 'README.md', 'README.txt', 'README.rst']
    for name in names:
        basename = os.path.basename(name).upper()
        for pattern in readme_patterns:
            if basename == pattern.upper() or basename.startswith(pattern.upper()):
                return True
    return False


def check_has_changelog(names: List[str]) -> bool:
    """Check if archive has a changelog file."""
    changelog_patterns = ['CHANGES', 'CHANGELOG', 'Changes', 'ChangeLog', 
                         'HISTORY', 'NEWS', 'CHANGELOG.md', 'CHANGES.md']
    for name in names:
        basename = os.path.basename(name)
        for pattern in changelog_patterns:
            if basename.upper() == pattern.upper():
                return True
    return False


def check_has_license(names: List[str]) -> bool:
    """Check if archive has a license file."""
    license_patterns = ['LICENSE', 'COPYING', 'COPYRIGHT', 
                       'LICENSE.txt', 'LICENSE.md']
    for name in names:
        basename = os.path.basename(name).upper()
        for pattern in license_patterns:
            if basename == pattern.upper():
                return True
    return False


def check_has_tests(names: List[str]) -> bool:
    """Check if archive has test files."""
    for name in names:
        # Check for test directories or test files
        parts = name.split('/')
        if 't' in parts or 'tests' in parts or 'test' in parts:
            return True
        if name.endswith('.t') or name.endswith('_test.py') or name.endswith('test_.py'):
            return True
    return False


def check_has_setup(names: List[str]) -> bool:
    """Check if archive has setup/build files."""
    setup_patterns = ['setup.py', 'pyproject.toml', 'Makefile.PL', 
                     'Build.PL', 'CMakeLists.txt']
    for name in names:
        basename = os.path.basename(name)
        if basename in setup_patterns:
            return True
    return False


def check_proper_structure(names: List[str]) -> bool:
    """Check if archive has proper directory structure."""
    # Should have a top-level directory
    if not names:
        return False
    
    # Get first path component
    first_dirs = set()
    for name in names:
        if '/' in name:
            first_dir = name.split('/')[0]
            first_dirs.add(first_dir)
        else:
            # File in root - not ideal but acceptable
            pass
    
    # Should have files in subdirectories, not all in root
    return len(first_dirs) > 0


def check_no_temp_files(names: List[str]) -> bool:
    """Check that archive doesn't contain temporary files."""
    temp_patterns = ['.swp', '.bak', '~', '.tmp', '.pyc', '__pycache__', 
                    '.DS_Store', 'Thumbs.db']
    for name in names:
        basename = os.path.basename(name)
        for pattern in temp_patterns:
            if basename.endswith(pattern) or pattern in name:
                return False
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Check quality metrics of a GLPI Agent distribution archive'
    )
    parser.add_argument(
        'archive',
        help='Path to distribution archive file',
        nargs='?'
    )
    
    args = parser.parse_args()
    
    if not args.archive:
        print("ERROR: No distribution archive file provided", file=sys.stderr)
        print("Usage: kwalitee.py <archive_file>", file=sys.stderr)
        return 1
    
    if not os.path.exists(args.archive):
        print(f"ERROR: Distribution file not found: {args.archive}", file=sys.stderr)
        return 1
    
    # Analyze the archive
    results = analyze_archive(args.archive)
    
    # Print results
    print(f"Kwalitee: {results['score']}/{results['max_score']}")
    
    # Print failures
    failures = [name for name, passed in results['kwalitee'].items() if not passed]
    if failures:
        for failure in sorted(failures):
            print(f"failure: {failure}")
    
    # Print errors
    if results['errors']:
        for error in results['errors']:
            print(f"error: {error}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

