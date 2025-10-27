import re
import os
from typing import Dict, Any, Optional, List

# Mock or simple implementations for GLPI Agent functions/tools
def get_canonical_string(value):
    if value is None:
        return None
    return str(value).strip()

def get_canonical_mac_address(value):
    if not value:
        return None
    if len(value) != 12:
        return None
    try:
        mac = ':'.join(value[i:i+2] for i in range(0, 12, 2)).upper()
        return mac
    except Exception:
        return None

def get_canonical_serial_number(value):
    # Mock for serial number canonicalization - trim and uppercase
    if value is None:
        return None
    return str(value).strip().upper()

def get_regexp_oid_match(oid):
    return re.compile(f'^{re.escape(oid)}')

# Mock YAML loading
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    def yaml_load_mock(file_path):
        # Mock YAML content for testing - structured as list with dict to match real YAML::Tiny->read
        return [{
            'sysobjectid': {
                'example': {
                    'oid': '.1.3.6.1.4.1.12345',
                    'rules': ['serial']  # List of rule names
                }
            },
            'rules': {
                'serial': {
                    'type': 'serial',
                    'valuetype': 'get-string',
                    'value': '.1.3.6.1.4.1.12345.1.0'
                }
            },
            'aliases': {}
        }]

# Mock base class for compatibility
class MibSupportTemplate:
    def __init__(self):
        self.device = None
        self._logger = None  # Mock logger

    def get(self, oid):
        # Mock SNMP get
        mock_values = {
            '.1.3.6.1.4.1.12345.1.0': 'SN123456789',
        }
        return mock_values.get(oid, None)

    def support(self):
        return 'sysObjectID:example'  # Mock

# Mock Config, Logger, etc.
class MockConfig:
    def __init__(self):
        self.confdir = '/tmp'  # Mock
        self.yaml = 'toolbox-plugin.yaml'

class MockLogger:
    def debug(self, msg):
        pass
    def debug2(self, msg):
        pass

class MockToolBox:
    @staticmethod
    def defaults():
        return {'confdir': '/tmp'}

mib_support = []

yaml_config = None
logger = None

def configure(agent=None, params=None):
    global logger, yaml_config
    logger = params.get('logger') if params else MockLogger()

    # Load defaults and plugin configuration
    config = MockConfig()
    confdir = config.confdir
    yamlconfig = os.path.join(confdir, config.yaml)

    if not YAML_AVAILABLE:
        if logger:
            logger.debug("Can't load needed YAML module")
        yaml_config = yaml_load_mock(yamlconfig)[0] if yaml_load_mock(yamlconfig) else {}
        _populate_mib_support(yaml_config)
        disabled = yaml_config.get('configuration', {}).get('mibsupport_disabled', 0)
        if disabled and str(disabled).lower() not in ['0', 'no']:
            return
        return  # Early return after mock setup

    # Real YAML case
    if not os.path.exists(yamlconfig):
        if logger:
            logger.debug2(f"{yamlconfig} configuration not found")
        return

    try:
        with open(yamlconfig, 'r') as f:
            yaml_loaded = yaml.safe_load(f)
        yaml_config = yaml_loaded[0] if isinstance(yaml_loaded, list) and yaml_loaded else yaml_loaded
        if not yaml_config:
            if logger:
                logger.debug(f"Failed to load {yamlconfig}")
            return
    except Exception as e:
        if logger:
            logger.debug(f"Failed to load {yamlconfig}: {e}")
        return

    disabled = yaml_config.get('configuration', {}).get('mibsupport_disabled', 0)
    if disabled and str(disabled).lower() not in ['0', 'no']:
        return

    _populate_mib_support(yaml_config)

def _populate_mib_support(yaml_data):
    global mib_support
    sysobjectid = yaml_data.get('sysobjectid', {})
    if sysobjectid:
        for name, data in sysobjectid.items():
            if not data:
                continue
            oid = data.get('oid')
            if not oid:
                continue
            match = get_regexp_oid_match(_normalized_oid(oid))
            if match:
                mib_support.append({
                    'name': f"sysObjectID:{name}",
                    'sysobjectid': match,
                })
            else:
                if logger:
                    logger.debug(f"{name} sysobjectid: match evaluation failure on {oid}")

    mibsupport = yaml_data.get('mibsupport', {})
    if mibsupport:
        for name, data in mibsupport.items():
            if not data:
                continue
            miboid = data.get('oid')
            if miboid:
                mib_support.append({
                    'name': f"mibSupport:{name}",
                    'oid': _normalized_oid(miboid),
                })

def _normalized_oid(oid, loop=0):
    if loop >= 10:
        return oid

    oid = re.sub(r'^enterprises', '.1.3.6.1.4.1', oid)
    oid = re.sub(r'^private', '.1.3.6.1.4', oid)
    oid = re.sub(r'^mib-2', '.1.3.6.1.2.1', oid)
    oid = re.sub(r'^iso', '.1', oid)

    global yaml_config
    aliases = yaml_config.get('aliases', {}) if yaml_config else {}
    updated = 0
    for alias, replacement in aliases.items():
        if re.match(f'^{re.escape(alias)}', oid):
            oid = re.sub(f'^{re.escape(alias)}', replacement, oid)
            updated += 1

    if updated:
        return _normalized_oid(oid, loop + 1)
    return oid

class ConfigurationPlugin(MibSupportTemplate):
    def get_firmware(self):
        return self._get_first_from_rules('firmware')

    def get_firmware_date(self):
        return self._get_first_from_rules('firmwaredate')

    def get_serial(self):
        return self._get_first_from_rules('serial')

    def get_mac_address(self):
        return self._get_first_from_rules('mac')

    def get_ip(self):
        return self._get_first_from_rules('ip')

    def get_model(self):
        return self._get_first_from_rules('model')

    def get_type(self):
        return self._get_first_from_rules('typedef')

    def get_manufacturer(self):
        return self._get_first_from_rules('manufacturer')

    def run(self):
        # Commented out in Perl, so empty
        pass

    def _get_first_from_rules(self, rule_type):
        global yaml_config, logger
        found = None
        for rule in self._get_rules(rule_type):
            type_val = rule.get('type', 'get-string')
            value = rule['value']
            oid = value if re.match(r'^\.[0-9.]+\d$', value) else _normalized_oid(value)
            if logger:
                logger.debug2(f"Matching rule value: {oid}")

            if type_val != 'raw' and type_val.startswith('get-') and re.match(r'^(\.[0-9.]+\d)$', oid):
                raw_value = self.get(oid)
                if type_val == 'get-mac':
                    found = get_canonical_mac_address(raw_value)
                elif type_val == 'get-serial':
                    found = get_canonical_serial_number(raw_value)
                else:
                    found = get_canonical_string(raw_value)
            else:
                found = value  # raw value if not OID

            if found and len(str(found)) > 0:
                if logger:
                    logger.debug2(f"Retrieved value: {found}")
                break
        return found

    def _get_rules(self, rule_type):
        global yaml_config, logger
        rules = yaml_config.get('rules') if yaml_config else {}
        if not rules:
            return []

        enabled_rules = []

        support_name = self.support()
        if not support_name:
            return []

        support_type, name = support_name.split(':', 1)
        if support_type == 'sysObjectID':
            sysobj_data = yaml_config.get('sysobjectid', {}).get(name)
            if sysobj_data and isinstance(sysobj_data.get('rules'), list):
                enabled_rules.extend(sysobj_data['rules'])
        elif support_type == 'mibSupport':
            mib_data = yaml_config.get('mibsupport', {}).get(name)
            if mib_data and isinstance(mib_data.get('rules'), list):
                enabled_rules.extend(mib_data['rules'])

        oids = []
        for rule in enabled_rules:
            if rule not in rules or rule_type != rules[rule].get('type'):
                continue
            oids.append({
                'value': rules[rule]['value'],
                'type': rules[rule].get('valuetype', 'get-string'),
            })
            if logger:
                logger.debug2(f"Matching rule: {rule}")
        return oids

# Call configure for initialization (mock agent and params)
configure(params={'logger': MockLogger()})

# For testing/standalone run (optional)
if __name__ == "__main__":
    config_plugin = ConfigurationPlugin()
    print("Firmware:", config_plugin.get_firmware())
    print("Serial:", config_plugin.get_serial())
    print("MAC:", config_plugin.get_mac_address())
    print("IP:", config_plugin.get_ip())
    print("Model:", config_plugin.get_model())
    print("Type:", config_plugin.get_type())
    print("Manufacturer:", config_plugin.get_manufacturer())
    config_plugin.run()
    print("Module loaded and run successfully without errors.")

"""
GLPI::Agent::SNMP::MibSupport::ConfigurationPlugin - Fully configurable
inventory module

The module can be used to extend devices support. It reads a YAML file which
contains the descriptions of matching cases and associated rules to apply.
"""
