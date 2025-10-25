# Tools Folder Conversion Summary

This document summarizes the conversion of Perl scripts and Bash scripts in the `tools/` folder to Python.

## Converted Scripts

### Perl to Python Conversions

1. **Changelog.py** (was Perl module)
   - Converted Perl package to Python module
   - Manages changelog file parsing and updates
   - Usage: `python Changelog.py <changelog_file>` or import as module

2. **json-inventory-validator.py** (was json-inventory-validator.pl)
   - Validates JSON inventory files against schema
   - Requires: `jsonschema`, `requests`
   - Usage: `python json-inventory-validator.py [--schema FILE] JSON_FILES`

3. **kwalitee.py** (was kwalitee.pl)
   - Checks quality metrics of distribution archives
   - Adapted from Perl Module::CPANTS::Analyse for Python
   - Usage: `python kwalitee.py <archive_file>`

4. **msi-signing.py** (was msi-signing.pl)
   - Signs Windows MSI installers using CodeSignTool
   - Requires: `requests`
   - Usage: `python msi-signing.py <folder> <msi_file>`
   - Environment variables: CST_CREDENTIALID, CST_USERNAME, CST_PASSWORD, CST_SECRET

5. **updatePciids.py** (was updatePciids.pl)
   - Updates pci.ids file from upstream sources
   - Updates changelog automatically
   - Requires: `requests`
   - Usage: `python updatePciids.py`

6. **updateSysobjectids.py** (was updateSysobjectids.pl)
   - Updates sysobject.ids file from GitHub
   - Updates changelog automatically
   - Requires: `requests`
   - Usage: `python updateSysobjectids.py`

7. **updateUsbids.py** (was updateUsbids.pl)
   - Updates usb.ids file from upstream sources
   - Updates changelog automatically
   - Requires: `requests`
   - Usage: `python updateUsbids.py`

8. **virustotal-report-analysis.py** (was virustotal-report-analysis.pl)
   - Checks VirusTotal reports for files
   - Requires: `requests`
   - Usage: `python virustotal-report-analysis.py [--sha256 HASH] [--debug] [--path PATH] FILES`
   - Environment variable: VT_API_KEY

### Bash to Python Conversions

9. **github-nightly-description.py** (was github-nightly-description.sh)
   - Generates nightly build descriptions for GitHub
   - Usage: `python github-nightly-description.py -v VERSION [--date DATE] [--header]`

10. **github-release-description.py** (was github-release-description.sh)
    - Generates release descriptions for GitHub
    - Usage: `python github-release-description.py [-v VERSION] [-t TAG] [--repo REPO]`
    - Uses GITHUB_REF environment variable if available

## Dependencies

All Python scripts require Python 3.6+. Additional dependencies:

```bash
# Install all dependencies
pip install requests jsonschema
```

### Per-script dependencies:
- **requests**: Required by most scripts for HTTP operations
- **jsonschema**: Required by json-inventory-validator.py

## Original Scripts

The original Perl and Bash scripts have been kept in place:
- `*.pl` files (Perl scripts)
- `*.sh` files (Bash scripts)

You can remove them once you've verified the Python versions work correctly for your use case.

## Platform Compatibility

- **Windows**: All Python scripts work on Windows (CMD/PowerShell)
- **Linux/Unix**: All scripts work, some use optional Unix commands like `touch` and `git`
- **macOS**: Fully compatible

Some scripts have optional Unix-specific features:
- File timestamp manipulation (uses `touch` command if available)
- Git integration (uses `git` command if available)

These features gracefully degrade on Windows or when commands are not available.

## Migration Notes

### For CI/CD Pipelines

If you're using these scripts in CI/CD pipelines, update your workflow files to use the Python versions:

**Before:**
```bash
perl tools/json-inventory-validator.pl inventory.json
./tools/github-nightly-description.sh --version 1.0
```

**After:**
```bash
python tools/json-inventory-validator.py inventory.json
python tools/github-nightly-description.py --version 1.0
```

### For Development

The Python scripts maintain the same command-line interface as the originals, so most usage patterns remain the same. Notable differences:

1. **Changelog.py**: Was a Perl module (package), now is a Python module. Import syntax changes from `use Changelog;` to `from Changelog import Changelog`.

2. **Environment Variables**: All environment variable handling remains the same.

3. **Exit Codes**: Python scripts maintain the same exit codes as the Perl/Bash versions.

## Testing

After conversion, test the scripts with:

```bash
# Test JSON validator
python tools/json-inventory-validator.py --help

# Test changelog
python tools/Changelog.py Changes

# Test updaters (requires internet)
python tools/updatePciids.py
python tools/updateUsbids.py
python tools/updateSysobjectids.py

# Test GitHub description generators
python tools/github-nightly-description.py --version 1.0.0 --header

# Test VirusTotal (requires VT_API_KEY)
export VT_API_KEY="your_key_here"
python tools/virustotal-report-analysis.py --sha256 "abc123..."
```

## Future Maintenance

All new tool development should use Python to maintain consistency with the rest of the GLPI Agent Python port.

