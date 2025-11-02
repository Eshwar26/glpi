#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages Megacli - Python Implementation

The module gets disk data from `megacli -PDlist` and `megacli -ShowSummary`.
`PDlist` provides s/n and model in a single 'Inquiry Data' string, and
`ShowSummary` helps unpacking this data.
"""

import re
from typing import Any, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import first, get_first_match, get_all_lines, get_canonical_size, get_canonical_manufacturer


class Megacli(InventoryModule):
    """LSI MegaCLI RAID controller inventory."""
    
    runMeIfTheseChecksFailed = ['GLPI::Agent::Task::Inventory::Linux::Storages::MegacliWithSmartctl']
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        from GLPI.Agent.Tools import can_run
        return can_run('megacli')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        count = get_first_match(
            command='megacli -adpCount',
            pattern=r'Controller Count: (\d+)'
        )
        if not count:
            return
        
        for adp in range(int(count)):
            adapter = Megacli._get_adp_enclosure(adp=adp)
            summary = Megacli._get_summary(adp=adp)
            pdlist = Megacli._get_pdlist(adp=adp)
            storages = Megacli._get_storages(adapter, pdlist, summary)
            
            for storage in storages.values():
                if inventory:
                    inventory.add_entry(
                        section='STORAGES',
                        entry=storage
                    )
    
    @staticmethod
    def _get_storages(adp: Dict, pdlist: Dict, summary: Dict) -> Dict:
        """Extract storage information from pdlist and summary."""
        storages = {}
        
        for pd_id, pd in pdlist.items():
            model = None
            vendor = None
            
            # Raw Size: 232.885 GB [0x1d1c5970 Sectors]
            raw_size = pd.get('Raw Size', '')
            size_match = re.match(r'^(.+)\s\[', raw_size)
            size = get_canonical_size(size_match.group(1)) if size_match else None
            
            firmware = pd.get('Device Firmware Level', '')
            
            storage = {
                'TYPE': 'disk',
                'FIRMWARE': firmware,
                'DESCRIPTION': pd.get('PD Type', ''),
                'DISKSIZE': size,
            }
            
            # Lookup the disk info in 'ShowSummary'
            def match_sum(s):
                encl_match = (
                    ('encl_id' in s and adp.get(s['encl_id']) == pd.get('Enclosure Device ID') and
                     'encl_pos' in s and s['encl_pos'] == pd.get('Enclosure position'))
                    or
                    ('encl_id' not in s and 'encl_pos' not in s)
                )
                slot_match = s.get('slot') == pd.get('Slot Number')
                return encl_match and slot_match
            
            sum_entry = first(match_sum, summary.values())
            
            if sum_entry:
                # 'HUC101212CSS'  <-- note it is incomplete
                model = sum_entry.get('Product Id', '')
                
                # 'HGST    HUC101212CSS600 U5E0KZGLG2HE'
                serial = pd.get('Inquiry Data', '')
                serial = serial.replace(firmware, '')  # remove firmware part
                
                vendor_id = sum_entry.get('Vendor Id', '')
                if vendor_id != 'ATA':
                    vendor = vendor_id
                    serial = serial.replace(vendor, '')  # remove vendor part
                
                serial = re.sub(rf'{re.escape(model)}\S*', '', serial)  # remove model part
                serial = re.sub(r'\s', '', serial)  # remove remaining spaces
                storage['SERIALNUMBER'] = serial
                
                # Restore complete model name:
                # HUC101212CSS --> HUC101212CSS600
                if model:
                    complete_match = re.search(rf'({re.escape(model)}(?:\S*))', pd.get('Inquiry Data', ''))
                    if complete_match:
                        model = complete_match.group(1).strip()
            
            # When Product ID ($model) looks like 'INTEL SSDSC2CW24'
            if model and re.match(r'^(\S+)\s+(\S+)$', model):
                parts = model.split()
                vendor = parts[0]  # 'INTEL'
                model = parts[1]   # 'SSDSC2CW24'
            
            storage['NAME'] = model
            storage['MODEL'] = model
            storage['MANUFACTURER'] = (
                get_canonical_manufacturer(vendor) if vendor
                else get_canonical_manufacturer(model) if model else None
            )
            
            storages[pd_id] = storage
        
        return storages
    
    @staticmethod
    def _get_adp_enclosure(**params) -> Dict:
        """Get adapter enclosure mapping."""
        adp = params.get('adp')
        if adp is not None:
            params['command'] = f'megacli -EncInfo -a{adp} -NoLog'
        
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        enclosure = {}
        encl_id = None
        
        for line in lines:
            encl_match = re.match(r'Enclosure (\d+):', line)
            if encl_match:
                encl_id = encl_match.group(1)
            
            device_match = re.search(r'Device ID\s+:\s+(\d+)', line)
            if device_match and encl_id is not None:
                enclosure[encl_id] = int(device_match.group(1))
        
        return enclosure
    
    @staticmethod
    def _get_summary(**params) -> Dict:
        """Get summary information from megacli."""
        adp = params.get('adp')
        if adp is not None:
            params['command'] = f'megacli -ShowSummary -a{adp} -NoLog'
        
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        # fast forward to relevant section
        while lines:
            line = lines.pop(0)
            if re.match(r'^\s+PD\s+$', line):
                break
        
        drive = {}
        n = -1
        
        for line in lines:
            # end of relevant section
            if re.match(r'^Storage$', line):
                break
            
            if re.search(r'Connector\s*:', line):
                n += 1
            
            # Connector: 0<Internal><Encl Pos 0 >: Slot 0
            match1 = re.search(r'Connector\s*:\s*(\d+)(?:<Internal>)?<Encl Pos (\d+) >: Slot (\d+)', line)
            if match1:
                drive[n] = {
                    'encl_id': int(match1.group(1)),
                    'encl_pos': match1.group(2),
                    'slot': int(match1.group(3)),
                }
            # Connector: 0<Internal>: Slot 0
            elif re.search(r'Connector\s*:\s*(?:\d+)(?:<Internal>):\s*Slot (\d+)', line):
                match2 = re.search(r'Slot (\d+)', line)
                drive[n] = {
                    'slot': int(match2.group(1)),
                }
            # Key: Value
            elif re.match(r'^\s*(.+\S)\s*:\s*(.+\S)', line):
                match3 = re.match(r'^\s*(.+\S)\s*:\s*(.+\S)', line)
                if n in drive:
                    drive[n][match3.group(1)] = match3.group(2)
        
        # delete non-disks
        to_delete = []
        for k, d in drive.items():
            if 'slot' not in d:
                to_delete.append(k)
            elif 'Product Id' in d and d['Product Id'] == 'SAS2 EXP BP':
                to_delete.append(k)
        for k in to_delete:
            del drive[k]
        
        return drive
    
    @staticmethod
    def _get_pdlist(**params) -> Dict:
        """Get physical drive list."""
        adp = params.get('adp')
        if adp is not None:
            params['command'] = f'megacli -PDlist -a{adp} -NoLog'
        
        lines = get_all_lines(**params)
        if not lines:
            return {}
        
        pdlist = {}
        n = 0
        
        for line in lines:
            match = re.match(r'^([^:]+)\s*:\s*(.*\S)', line)
            if not match:
                continue
            
            key, val = match.groups()
            if re.search(r'Enclosure Device ID', key):
                n += 1
            if n not in pdlist:
                pdlist[n] = {}
            pdlist[n][key] = val
        
        return pdlist
