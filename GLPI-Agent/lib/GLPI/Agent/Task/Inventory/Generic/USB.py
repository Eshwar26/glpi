# glpi_agent/task/inventory/generic/usb.py

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run, get_all_lines, trim_whitespace, get_sanitized_string, empty
from glpi_agent.tools.generic import get_usb_device_vendor


class USB(InventoryModule):
    """Generic USB inventory module."""
    
    @staticmethod
    def category():
        return "usb"
    
    def is_enabled(self, **params):
        return can_run('lsusb')
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        datadir = params.get('datadir')
        
        for device in self._get_devices(logger=logger, datadir=datadir):
            inventory.add_entry(
                section='USBDEVICES',
                entry=device
            )
    
    def _get_devices(self, **params):
        devices = []
        
        for device in self._get_devices_from_lsusb(**params):
            if not device.get('PRODUCTID'):
                continue
            if not device.get('VENDORID'):
                continue
            
            if device.get('SERIAL') is not None and len(device['SERIAL']) < 5:
                device['SERIAL'] = None
            
            vendor = get_usb_device_vendor(id=device['VENDORID'], **params)
            if vendor:
                device['MANUFACTURER'] = vendor['name']
                entry = vendor.get('devices', {}).get(device['PRODUCTID'])
                if entry:
                    device['CAPTION'] = device['NAME'] = entry['name']
            
            devices.append(device)
        
        return devices
    
    def _get_devices_from_lsusb(self, **params):
        params.setdefault('command', 'lsusb -v')
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        devices = []
        device = None
        hub = False
        selfpowered = False
        
        for line in lines:
            if line.strip() == '':
                # Ignore any self-powered hub considering they are the embedded usb support hardware
                if device and not (hub and selfpowered):
                    devices.append(device)
                device = None
                hub = False
                selfpowered = False
                
            elif 'idVendor' in line:
                import re
                match = re.search(r'idVendor\s*0x(\w+)', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    device['VENDORID'] = match.group(1)
                    
            elif 'idProduct' in line:
                import re
                match = re.search(r'idProduct\s*0x(\w+)', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    device['PRODUCTID'] = match.group(1)
                    
            elif 'iProduct' in line:
                import re
                match = re.search(r'iProduct\s+\d+\s+(.*)$', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    name = trim_whitespace(get_sanitized_string(match.group(1)))
                    if not empty(name):
                        device['NAME'] = name
                        
            elif 'iManufacturer' in line:
                import re
                match = re.search(r'iManufacturer\s+\d+\s+(.*)$', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    manufacturer = trim_whitespace(get_sanitized_string(match.group(1)))
                    if not empty(manufacturer):
                        device['MANUFACTURER'] = manufacturer
                        
            elif 'iSerial' in line:
                import re
                match = re.search(r'iSerial\s*\d+\s(.*)$', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    i_serial = trim_whitespace(match.group(1))
                    # 1. Support manufacturers wrongly using iSerial with fields definition
                    # 2. Don't include serials with colons as they seems to be an internal id for hub layers
                    sn_match = re.search(r'S/N:([^: ]+)', i_serial)
                    if sn_match:
                        device['SERIAL'] = sn_match.group(1)
                    elif not empty(i_serial) and ':' not in i_serial:
                        device['SERIAL'] = i_serial
                        
            elif 'bInterfaceClass' in line:
                import re
                match = re.search(r'bInterfaceClass\s*(\d+)', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    device['CLASS'] = match.group(1)
                    
            elif 'bInterfaceSubClass' in line:
                import re
                match = re.search(r'bInterfaceSubClass\s*(\d+)', line, re.IGNORECASE)
                if match:
                    if device is None:
                        device = {}
                    device['SUBCLASS'] = match.group(1)
                    
            elif 'bDeviceClass' in line:
                import re
                match = re.search(r'bDeviceClass\s*9\s+Hub', line, re.IGNORECASE)
                if match:
                    hub = True
                    
            elif 'Device Status:' in line:
                import re
                match = re.search(r'Device Status:\s*(0x[0-9a-f]{4})', line, re.IGNORECASE)
                if match:
                    selfpowered = int(match.group(1), 16) & 1
        
        if device and not (hub and selfpowered):
            devices.append(device)
        
        return devices