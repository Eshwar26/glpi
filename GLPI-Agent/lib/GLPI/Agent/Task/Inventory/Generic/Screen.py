# glpi_agent/task/inventory/generic/screen.py

import platform
import os
import base64
from pathlib import Path

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run, can_read, get_all_lines, has_folder
from glpi_agent.tools.screen import Screen
from glpi_agent.tools.generic import get_edid_vendor


class ScreenModule(InventoryModule):
    """Generic Screen inventory module."""
    
    @staticmethod
    def category():
        return "monitor"
    
    def is_enabled(self, **params):
        return True
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        options = {
            'logger': params.get('logger'),
            'datadir': params.get('datadir'),
            'format': inventory.get_format() or 'json',
            'remote': inventory.get_remote()
        }
        
        for screen in self._get_screens(**options):
            inventory.add_entry(
                section='MONITORS',
                entry=screen
            )
    
    def _get_edid_info(self, **params):
        try:
            from parse_edid import parse_edid, check_parsed_edid
        except ImportError:
            logger = params.get('logger')
            if logger:
                logger.debug(
                    "parse_edid module not available, unable to parse EDID data"
                )
            return None
        
        edid = parse_edid(params['edid'])
        error = check_parsed_edid(edid)
        if error:
            logger = params.get('logger')
            if logger:
                logger.debug(f"bad edid: {error}")
            # Don't return if edid is finally partially parsed
            if not (edid.get('monitor_name') and edid.get('week') and
                    edid.get('year') and edid.get('serial_number')):
                return None
        
        screen = Screen(edid=edid, **params)
        
        info = {
            'CAPTION': screen.caption() or None,
            'DESCRIPTION': screen.week_year_manufacture(),
            'MANUFACTURER': screen.manufacturer(),
            'SERIAL': screen.serial()
        }
        
        # Add ALTSERIAL if defined by Screen object
        altserial = screen.altserial()
        if altserial:
            info['ALTSERIAL'] = altserial
        
        return info
    
    def _get_screens_from_windows(self, **params):
        try:
            from glpi_agent.tools.win32 import get_wmi_objects, get_registry_value
        except ImportError:
            return []
        
        screens = []
        
        # VideoOutputTechnology table
        ports = {
            '-1': 'Other',
            '0': 'VGA',
            '1': 'S-Video',
            '2': 'Composite',
            '3': 'YUV',
            '4': 'DVI',
            '5': 'HDMI',
            '6': 'LVDS',
            '8': 'D-Jpn',
            '9': 'SDI',
            '10': 'DisplayPort',
            '11': 'eDisplayPort',
            '12': 'UDI',
            '13': 'eUDI',
            '14': 'SDTV',
            '15': 'Miracast'
        }
        
        # Vista and upper, able to get the second screen
        for obj in get_wmi_objects(
            moniker='winmgmts:{impersonationLevel=impersonate,authenticationLevel=Pkt}!//./root/wmi',
            class_name='WMIMonitorConnectionParams',
            properties=['Active', 'InstanceName', 'VideoOutputTechnology']
        ):
            if not obj.get('InstanceName') or not obj.get('Active'):
                continue
            
            instance_name = obj['InstanceName'].rsplit('_', 1)[0]
            screen = {'id': instance_name}
            
            # Skip setting monitor port as it is not used on server-side and this
            # does not respect json format
            fmt = params.get('format', 'json')
            if fmt != 'json' and 'VideoOutputTechnology' in obj:
                port = str(obj['VideoOutputTechnology'])
                if port in ports:
                    screen['PORT'] = ports[port]
            
            screens.append(screen)
        
        # The generic Win32_DesktopMonitor class, the second screen will be missing
        for obj in get_wmi_objects(
            class_name='Win32_DesktopMonitor',
            properties=['Caption', 'MonitorManufacturer', 'MonitorType', 
                       'PNPDeviceID', 'Availability']
        ):
            if not obj.get('Availability') or not obj.get('PNPDeviceID'):
                continue
            if obj['Availability'] != 3:
                continue
            
            screens.append({
                'id': obj['PNPDeviceID'],
                'NAME': obj.get('Caption'),
                'MANUFACTURER': obj.get('MonitorManufacturer'),
                'CAPTION': obj.get('Caption')
            })
        
        logger = params.get('logger')
        for screen in screens:
            if not screen.get('id'):
                continue
            
            # Support overrided EDID block
            device_id = screen['id']
            edid = get_registry_value(
                path=f"HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/Enum/{device_id}/Device Parameters/EDID_OVERRIDE",
                logger=logger
            )
            if not edid:
                edid = get_registry_value(
                    path=f"HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/Enum/{device_id}/Device Parameters/EDID",
                    method="GetBinaryValue",
                    logger=logger
                )
            
            if edid and edid.strip():
                screen['edid'] = edid
            
            del screen['id']
            if 'edid' not in screen or not screen['edid']:
                screen.pop('edid', None)
        
        return screens
    
    def _get_screens_from_unix(self, **params):
        logger = params.get('logger')
        if logger:
            logger.debug("retrieving EDID data:")
        
        if has_folder('/sys/devices'):
            screens = []
            
            if params.get('remote'):
                from glpi_agent.tools import Glob
                cards = Glob("/sys/devices/*/*/drm/* /sys/devices/*/*/*/drm/*")
                # Filter out links
                ctrls = Glob("/sys/devices/*/*/drm/* /sys/devices/*/*/*/drm/*", "-h")
                if cards and ctrls:
                    cards = [card for card in cards if card not in ctrls]
                
                for card in cards:
                    edid_files = Glob(f"{card}/*/edid")
                    if not edid_files:
                        continue
                    for sysfile in edid_files:
                        edid = get_all_lines(file=sysfile)
                        if edid:
                            screens.append({'edid': edid})
            else:
                import os
                for root, dirs, files in os.walk('/sys/devices'):
                    for filename in files:
                        if filename == 'edid':
                            filepath = os.path.join(root, filename)
                            if can_read(filepath):
                                edid = get_all_lines(file=filepath)
                                if edid:
                                    screens.append({'edid': edid})
            
            if logger:
                logger.debug_result(
                    action='reading /sys/devices content',
                    data=len(screens)
                )
            
            if screens:
                return screens
        else:
            if logger:
                logger.debug_result(
                    action='reading /sys/devices content',
                    status='directory not available'
                )
        
        if can_run('monitor-get-edid-using-vbe'):
            edid = get_all_lines(command='monitor-get-edid-using-vbe')
            if logger:
                logger.debug_result(
                    action='running monitor-get-edid-using-vbe command',
                    data=edid
                )
            if edid:
                return [{'edid': edid}]
        else:
            if logger:
                logger.debug_result(
                    action='running monitor-get-edid-using-vbe command',
                    status='command not available'
                )
        
        if can_run('monitor-get-edid'):
            edid = get_all_lines(command='monitor-get-edid')
            if logger:
                logger.debug_result(
                    action='running monitor-get-edid command',
                    data=edid
                )
            if edid:
                return [{'edid': edid}]
        else:
            if logger:
                logger.debug_result(
                    action='running monitor-get-edid command',
                    status='command not available'
                )
        
        if can_run('get-edid'):
            edid = None
            for _ in range(5):  # Sometimes get-edid returns an empty string...
                edid = get_all_lines(command='get-edid')
                if edid:
                    break
            if logger:
                logger.debug_result(
                    action='running get-edid command',
                    data=edid
                )
            if edid:
                return [{'edid': edid}]
        else:
            if logger:
                logger.debug_result(
                    action='running get-edid command',
                    status='command not available'
                )
        
        return []
    
    def _get_screens_from_macos(self, **params):
        logger = params.get('logger')
        
        if logger:
            logger.debug("retrieving AppleBacklightDisplay and AppleDisplay datas:")
        
        try:
            from glpi_agent.tools.macos import get_io_devices
        except ImportError:
            return self._get_screens_from_unix(**params)
        
        screens = []
        displays = get_io_devices(
            class_name='AppleBacklightDisplay',
            options='-r -lw0 -d 1',
            logger=logger
        )
        
        displays.extend(get_io_devices(
            class_name='AppleDisplay',
            options='-r -lw0 -d 1',
            logger=logger
        ))
        
        displays.extend(get_io_devices(
            class_name='AppleCLCD2',
            options='-r -lw0 -d 1',
            logger=logger
        ))
        
        for display in displays:
            screen = {}
            
            if display.get('IODisplayCapabilityString'):
                import re
                match = re.search(r'model\((.*)\)', display['IODisplayCapabilityString'])
                if match:
                    screen['CAPTION'] = match.group(1)
            
            if display.get('IODisplayEDID'):
                edid_str = display['IODisplayEDID']
                if (edid_str and 
                    all(c in '0123456789abcdefABCDEF' for c in edid_str) and
                    len(edid_str) in (256, 512)):
                    screen['edid'] = bytes.fromhex(edid_str)
            
            if (display.get('DisplayAttributes') and 
                isinstance(display['DisplayAttributes'], dict) and
                isinstance(display['DisplayAttributes'].get('ProductAttributes'), dict)):
                
                attributes = display['DisplayAttributes']['ProductAttributes']
                
                if attributes.get('ProductName'):
                    screen['CAPTION'] = attributes['ProductName']
                if attributes.get('AlphanumericSerialNumber'):
                    screen['SERIAL'] = attributes['AlphanumericSerialNumber']
                if attributes.get('SerialNumber'):
                    screen['ALTSERIAL'] = attributes['SerialNumber']
                if attributes.get('ManufacturerID'):
                    manufacturer = (get_edid_vendor(id=attributes['ManufacturerID']) or 
                                  attributes['ManufacturerID'])
                    screen['MANUFACTURER'] = manufacturer
                if attributes.get('WeekOfManufacture') and attributes.get('YearOfManufacture'):
                    screen['DESCRIPTION'] = f"{attributes['WeekOfManufacture']}/{attributes['YearOfManufacture']}"
            
            if screen:
                screens.append(screen)
        
        if screens:
            return screens
        
        # Try unix commands if no screen is detected
        return self._get_screens_from_unix(**params)
    
    def _get_screens(self, **params):
        screens_dict = {}
        
        # params['screens'] can only be set during tests
        if params.get('screens'):
            screens_list = params['screens']
        elif platform.system() == 'Windows':
            screens_list = self._get_screens_from_windows(**params)
        elif platform.system() == 'Darwin':
            screens_list = self._get_screens_from_macos(**params)
        else:
            screens_list = self._get_screens_from_unix(**params)
        
        for screen in screens_list:
            if not screen.get('edid') and not (screen.get('SERIAL') and screen.get('CAPTION')):
                continue
            
            if screen.get('edid'):
                info = self._get_edid_info(
                    edid=screen['edid'],
                    logger=params.get('logger'),
                    datadir=params.get('datadir')
                )
                if info:
                    screen['CAPTION'] = info['CAPTION']
                    screen['DESCRIPTION'] = info['DESCRIPTION']
                    screen['MANUFACTURER'] = info['MANUFACTURER']
                    screen['SERIAL'] = info['SERIAL']
                    if info.get('ALTSERIAL'):
                        screen['ALTSERIAL'] = info['ALTSERIAL']
                
                screen['BASE64'] = base64.b64encode(screen['edid']).decode('ascii')
                del screen['edid']
            
            # Add or merge found values
            serial = screen.get('SERIAL') or screen.get('BASE64')
            if serial not in screens_dict:
                screens_dict[serial] = screen
            else:
                for key, value in screen.items():
                    if key in screens_dict[serial]:
                        if screens_dict[serial][key] != value:
                            logger = params.get('logger')
                            if logger:
                                logger.warning(
                                    f"Not merging not coherent {key} value for screen associated to {serial} serial number"
                                )
                        continue
                    screens_dict[serial][key] = value
        
        return [screens_dict[serial] for serial in sorted(screens_dict.keys())]